from datetime import datetime, timedelta, timezone
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, delete

log = logging.getLogger(__name__)
_scheduler = BlockingScheduler(timezone='Europe/Berlin')


def run_scheduler(app):
    _scheduler.add_job(
        lambda: _purge_expired_tokens(app),
        CronTrigger(minute=0),
        id='purge_tokens',
        replace_existing=True,
    )
    _scheduler.add_job(
        lambda: _purge_old_logs(app),
        CronTrigger(hour=3, minute=0),
        id='purge_logs',
        replace_existing=True,
    )
    _scheduler.add_job(
        lambda: _purge_old_volunteers(app),
        CronTrigger(day=1, hour=4, minute=0),  # monatlich am 1. um 04:00
        id='purge_volunteers',
        replace_existing=True,
    )
    _scheduler.add_job(
        lambda: _send_reminders(app),
        CronTrigger(hour=8, minute=0),  # täglich 08:00 – Erinnerungsmails
        id='send_reminders',
        replace_existing=True,
    )
    _scheduler.add_job(
        lambda: _send_organizer_digest(app),
        CronTrigger(hour=6, minute=0),  # täglich 06:00 – Organisatoren-Digest
        id='organizer_digest',
        replace_existing=True,
    )

    log.info('APScheduler gestartet (separater Prozess)')
    _scheduler.start()  # blockiert


def _purge_expired_tokens(app):
    with app.app_context():
        try:
            from ..extensions import db
            from ..models import Admin, Organizer, Volunteer
            now = datetime.now(timezone.utc)
            for model in (Admin, Organizer, Volunteer):
                expired = db.session.scalars(
                    select(model).filter(
                        model.reset_token.isnot(None),
                        model.reset_token_expires < now,
                    )
                ).all()
                for user in expired:
                    user.clear_reset_token()
            db.session.commit()
            log.debug('Abgelaufene Reset-Tokens bereinigt')
        except Exception:
            log.exception('Token-Bereinigung fehlgeschlagen')


def _purge_old_logs(app):
    with app.app_context():
        try:
            from ..extensions import db
            from ..models import ActivityLog, GlobalSettings
            gs = db.session.scalars(select(GlobalSettings)).first()
            months = gs.log_retention_months if gs else 3
            cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
            deleted = db.session.execute(
                delete(ActivityLog).filter(ActivityLog.timestamp < cutoff)
            ).rowcount
            db.session.commit()
            log.info('Protokoll-Bereinigung: %d Einträge gelöscht (älter als %d Monate)',
                     deleted, months)
        except Exception:
            log.exception('Protokoll-Bereinigung fehlgeschlagen')


def _purge_old_volunteers(app):
    """DSGVO Art. 5 – löscht inaktive Volunteers nach Aufbewahrungsfrist."""
    with app.app_context():
        try:
            from ..extensions import db
            from ..models import GlobalSettings, Volunteer, Registration, Shift, EventDate

            gs = db.session.scalars(select(GlobalSettings)).first()
            if not gs or not gs.volunteer_retention_months:
                return

            cutoff = datetime.now(timezone.utc) - timedelta(days=gs.volunteer_retention_months * 30)
            candidates = db.session.scalars(
                select(Volunteer).filter(
                    Volunteer.deleted_at.is_(None),
                    Volunteer.created_at < cutoff,
                )
            ).all()

            count = 0
            for v in candidates:
                # Nicht löschen wenn Volunteer noch zukünftige Dienste hat
                has_future = db.session.scalars(
                    select(Registration)
                    .join(Shift, Registration.shift_id == Shift.id)
                    .join(EventDate, Shift.event_date_id == EventDate.id)
                    .filter(
                        Registration.volunteer_id == v.id,
                        EventDate.date >= datetime.now(timezone.utc).date(),
                    )
                ).first()
                if not has_future:
                    v.soft_delete()
                    count += 1

            if count:
                db.session.commit()
                log.info('DSGVO-Bereinigung: %d Volunteers nach %d Monaten gelöscht',
                         count, gs.volunteer_retention_months)
        except Exception:
            log.exception('DSGVO-Volunteer-Bereinigung fehlgeschlagen')


def _send_reminders(app):
    """Sendet täglich um 08:00 Erinnerungsmails an Volunteers mit aktivierten Benachrichtigungen."""
    with app.app_context():
        try:
            import pytz
            from ..extensions import db
            from ..models import (
                Volunteer, Registration, Shift, EventDate,
                FoodDonation, FoodDonationType, Instance,
            )
            from ..utils.mail import is_mail_configured, send_mail, get_effective_logo_for_email, build_reminder_email
            from ..utils.settings_cache import get_global_settings, get_site_settings

            if not is_mail_configured():
                return

            gs = get_global_settings()
            tz_name = gs.timezone if gs and gs.timezone else 'Europe/Berlin'
            tz = pytz.timezone(tz_name)
            now_local = datetime.now(tz)
            tomorrow = (now_local + timedelta(days=1)).date()

            # UTC-Grenzen für den morgigen Tag (für delivery_datetime-Vergleich)
            tomorrow_start = tz.localize(
                datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
            ).astimezone(timezone.utc)
            tomorrow_end = tz.localize(
                datetime(tomorrow.year, tomorrow.month, tomorrow.day, 23, 59, 59)
            ).astimezone(timezone.utc)

            base_url = app.config.get('FRONTEND_URL', '')
            copyright_text = gs.copyright_text if gs else None

            volunteers = db.session.scalars(
                select(Volunteer).filter(
                    Volunteer.notifications_enabled.is_(True),
                    Volunteer.email.isnot(None),
                    Volunteer.deleted_at.is_(None),
                )
            ).all()

            for v in volunteers:
                shifts_tomorrow = db.session.scalars(
                    select(Registration)
                    .join(Shift, Registration.shift_id == Shift.id)
                    .join(EventDate, Shift.event_date_id == EventDate.id)
                    .filter(
                        Registration.volunteer_id == v.id,
                        EventDate.date == tomorrow,
                    )
                ).all()

                food_tomorrow = db.session.scalars(
                    select(FoodDonation)
                    .join(FoodDonationType, FoodDonation.food_type_id == FoodDonationType.id)
                    .filter(
                        FoodDonation.volunteer_id == v.id,
                        FoodDonationType.delivery_datetime >= tomorrow_start,
                        FoodDonationType.delivery_datetime <= tomorrow_end,
                    )
                ).all()

                if not shifts_tomorrow and not food_tomorrow:
                    continue

                settings = get_site_settings(v.instance_id)
                instance = db.session.get(Instance, v.instance_id)
                title = settings.site_title if settings else (instance.name if instance else 'Standdienst')
                primary_color = settings.primary_color if settings else None
                logo_url = get_effective_logo_for_email(
                    settings.logo_filename if settings else None, base_url
                )
                slug = instance.slug if instance else ''

                shift_data = [
                    {
                        'stand': r.shift.stand.name,
                        'time': f'{r.shift.start_time.strftime("%H:%M")}–{r.shift.end_time.strftime("%H:%M")}',
                    }
                    for r in shifts_tomorrow
                ]
                food_data = [
                    {
                        'name': d.food_type.name,
                        'description': d.description,
                        'delivery_time': (
                            d.food_type.delivery_datetime.astimezone(tz).strftime('%H:%M')
                            if d.food_type.delivery_datetime else None
                        ),
                        'delivery_location': d.food_type.delivery_location,
                    }
                    for d in food_tomorrow
                ]

                try:
                    opt_out_url = f'{base_url}/{slug}/profile'
                    kw = dict(slug=slug, logo_url=logo_url,
                              copyright_text=copyright_text, opt_out_url=opt_out_url,
                              show_branding=settings.branding_enabled if settings else True)
                    if primary_color:
                        kw['primary_color'] = primary_color
                    send_mail(
                        v.email,
                        f'Erinnerung für morgen – {title}',
                        build_reminder_email(v.name, shift_data, food_data, title, base_url, **kw),
                        sender_name=title,
                    )
                    log.info('Erinnerungsmail gesendet: volunteer_id=%d', v.id)
                except Exception:
                    log.exception('Erinnerungsmail fehlgeschlagen: volunteer_id=%d', v.id)

        except Exception:
            log.exception('Erinnerungs-Job fehlgeschlagen')


def _send_organizer_digest(app):
    """Täglich 06:00 – Zusammenfassung der gestrigen Änderungen an Organisatoren und Admins."""
    with app.app_context():
        try:
            import pytz
            from ..extensions import db
            from ..models import (
                Admin, Organizer, Registration, ActivityLog, FoodDonation,
                FoodDonationType, Shift, Stand, EventDate, Instance,
            )
            from ..models.instance import (
                organizer_instances as oi_table,
                admin_digest_subscriptions as ads_table,
            )
            from ..utils.mail import is_mail_configured, send_mail, build_organizer_digest_email, get_effective_logo_for_email
            from ..utils.settings_cache import get_global_settings, get_site_settings

            if not is_mail_configured():
                return

            gs = get_global_settings()
            tz_name = gs.timezone if gs and gs.timezone else 'Europe/Berlin'
            tz = pytz.timezone(tz_name)
            now_local = datetime.now(tz)
            yesterday = (now_local - timedelta(days=1)).date()
            day_start = tz.localize(datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)).astimezone(timezone.utc)
            day_end = tz.localize(datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)).astimezone(timezone.utc)

            base_url = app.config.get('FRONTEND_URL', '')
            copyright_text = gs.copyright_text if gs else None
            date_label = yesterday.strftime('%d.%m.%Y')
            opt_out_url = f'{base_url}/admin/profile'

            def _collect_data(instance_id):
                regs = db.session.execute(
                    select(Registration, Shift, Stand)
                    .join(Shift, Registration.shift_id == Shift.id)
                    .join(Stand, Shift.stand_id == Stand.id)
                    .filter(
                        Stand.instance_id == instance_id,
                        Registration.registered_at >= day_start,
                        Registration.registered_at <= day_end,
                    )
                ).all()
                cancels = db.session.scalars(
                    select(ActivityLog).filter(
                        ActivityLog.instance_id == instance_id,
                        ActivityLog.event_type == ActivityLog.SHIFT_UNREGISTER,
                        ActivityLog.timestamp >= day_start,
                        ActivityLog.timestamp <= day_end,
                    )
                ).all()
                foods = db.session.scalars(
                    select(FoodDonation)
                    .join(FoodDonationType, FoodDonation.food_type_id == FoodDonationType.id)
                    .filter(
                        FoodDonationType.instance_id == instance_id,
                        FoodDonation.registered_at >= day_start,
                        FoodDonation.registered_at <= day_end,
                    )
                ).all()
                return regs, cancels, foods

            def _send_digest(recipient_email, recipient_name, instance, regs, cancels, foods):
                settings = get_site_settings(instance.id)
                title = settings.site_title if settings else instance.name
                primary_color = settings.primary_color if settings else None
                logo_url = get_effective_logo_for_email(
                    settings.logo_filename if settings else None, base_url
                )
                reg_data = [
                    {
                        'name': (r.volunteer.display_name if r.volunteer else r.guest_name) or '—',
                        'stand': s.name,
                        'time': f'{sh.start_time.strftime("%H:%M")}–{sh.end_time.strftime("%H:%M")}',
                    }
                    for r, sh, s in regs
                ]
                cancel_data = [
                    {'name': c.volunteer_name or '—', 'stand': '', 'time': c.details or ''}
                    for c in cancels
                ]
                food_data = [
                    {
                        'name': (f.volunteer.display_name if f.volunteer else f.guest_name) or '—',
                        'food_type': f.food_type.name if f.food_type else '—',
                        'description': f.description,
                    }
                    for f in foods
                    if f.food_type
                ]
                kw = dict(logo_url=logo_url, copyright_text=copyright_text, opt_out_url=opt_out_url,
                          show_branding=settings.branding_enabled if settings else True)
                if primary_color:
                    kw['primary_color'] = primary_color
                send_mail(
                    recipient_email,
                    f'Tagesübersicht {date_label} – {title}',
                    build_organizer_digest_email(
                        recipient_name or recipient_email,
                        title, date_label, reg_data, cancel_data, food_data,
                        base_url, instance.slug, **kw,
                    ),
                    sender_name=title,
                )

            # ── Organisatoren: per-Instanz digest_enabled ──────────────────
            enabled_oi = db.session.execute(
                oi_table.select().where(oi_table.c.digest_enabled == True)
            ).fetchall()
            from collections import defaultdict
            org_inst_ids = defaultdict(set)
            for row in enabled_oi:
                org_inst_ids[row.organizer_id].add(row.instance_id)

            for org_id, inst_ids in org_inst_ids.items():
                org = db.session.scalars(
                    select(Organizer).filter(
                        Organizer.id == org_id,
                        Organizer.email.isnot(None),
                    )
                ).first()
                if not org:
                    continue
                for instance in db.session.scalars(select(Instance).filter(Instance.id.in_(inst_ids))).all():
                    regs, cancels, foods = _collect_data(instance.id)
                    if not regs and not cancels and not foods:
                        continue
                    try:
                        _send_digest(org.email, org.name or org.email, instance, regs, cancels, foods)
                        log.info('Organizer-Digest gesendet: organizer_id=%d, instance=%s', org.id, instance.slug)
                    except Exception:
                        log.exception('Organizer-Digest fehlgeschlagen: organizer_id=%d, instance=%s', org.id, instance.slug)

            # ── Globale Admins: explizit abonnierte Instanzen ──────────────
            admin_subs = db.session.execute(ads_table.select()).fetchall()
            admin_inst_ids = defaultdict(set)
            for row in admin_subs:
                admin_inst_ids[row.admin_id].add(row.instance_id)

            for admin_id, inst_ids in admin_inst_ids.items():
                admin = db.session.scalars(
                    select(Admin).filter(
                        Admin.id == admin_id,
                        Admin.email.isnot(None),
                    )
                ).first()
                if not admin:
                    continue
                for instance in db.session.scalars(select(Instance).filter(Instance.id.in_(inst_ids))).all():
                    regs, cancels, foods = _collect_data(instance.id)
                    if not regs and not cancels and not foods:
                        continue
                    try:
                        _send_digest(admin.email, admin.name or admin.email, instance, regs, cancels, foods)
                        log.info('Admin-Digest gesendet: admin_id=%d, instance=%s', admin.id, instance.slug)
                    except Exception:
                        log.exception('Admin-Digest fehlgeschlagen: admin_id=%d, instance=%s', admin.id, instance.slug)

        except Exception:
            log.exception('Organizer-Digest-Job fehlgeschlagen')


