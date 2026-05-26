from datetime import datetime, timedelta, timezone
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)
_scheduler = BackgroundScheduler(timezone='Europe/Berlin')


def _redis_lock(app, key: str, ttl: int = 3590) -> bool:
    """Nur ein Gunicorn-Worker darf einen Job gleichzeitig ausführen.

    Gibt True zurück wenn dieser Worker die Sperre erworben hat (oder Redis
    nicht verfügbar ist – dann wird der Job in allen Workern ausgeführt).
    """
    uri = app.config.get('RATELIMIT_STORAGE_URI', 'memory://')
    if not uri.startswith('redis://'):
        return True  # kein Redis → Single-Worker-Dev, kein Lock nötig
    try:
        import redis as redis_lib
        r = redis_lib.from_url(uri, socket_connect_timeout=2)
        acquired = r.set(f'sched:{key}', '1', nx=True, ex=ttl)
        r.close()
        return bool(acquired)
    except Exception:
        log.warning('Redis-Lock für Scheduler-Job %s nicht erreichbar', key)
        return True


def init_scheduler(app):
    if app.config.get('TESTING'):
        return

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
        lambda: _run_smb_backup(app),
        CronTrigger(hour=2, minute=30),
        id='smb_backup',
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
        CronTrigger(hour=18, minute=0),  # täglich 18:00 – Organisatoren-Digest
        id='organizer_digest',
        replace_existing=True,
    )

    _scheduler.start()
    log.info('APScheduler gestartet')


def _purge_expired_tokens(app):
    if not _redis_lock(app, 'purge_tokens'):
        return
    with app.app_context():
        try:
            from ..extensions import db
            from ..models import Admin, Organizer, Volunteer
            now = datetime.now(timezone.utc)
            for model in (Admin, Organizer, Volunteer):
                expired = model.query.filter(
                    model.reset_token.isnot(None),
                    model.reset_token_expires < now,
                ).all()
                for user in expired:
                    user.clear_reset_token()
            db.session.commit()
            log.debug('Abgelaufene Reset-Tokens bereinigt')
        except Exception:
            log.exception('Token-Bereinigung fehlgeschlagen')


def _purge_old_logs(app):
    if not _redis_lock(app, 'purge_logs', ttl=86000):
        return
    with app.app_context():
        try:
            from ..extensions import db
            from ..models import ActivityLog, GlobalSettings
            gs = GlobalSettings.query.first()
            months = gs.log_retention_months if gs else 3
            cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
            deleted = ActivityLog.query.filter(ActivityLog.created_at < cutoff).delete()
            db.session.commit()
            log.info('Protokoll-Bereinigung: %d Einträge gelöscht (älter als %d Monate)',
                     deleted, months)
        except Exception:
            log.exception('Protokoll-Bereinigung fehlgeschlagen')


def _purge_old_volunteers(app):
    """DSGVO Art. 5 – löscht inaktive Volunteers nach Aufbewahrungsfrist."""
    if not _redis_lock(app, 'purge_volunteers', ttl=86000):
        return
    with app.app_context():
        try:
            from ..extensions import db
            from ..models import GlobalSettings, Volunteer, Registration, Shift, EventDate

            gs = GlobalSettings.query.first()
            if not gs or not gs.volunteer_retention_months:
                return

            cutoff = datetime.now(timezone.utc) - timedelta(days=gs.volunteer_retention_months * 30)
            candidates = Volunteer.query.filter(
                Volunteer.deleted_at.is_(None),
                Volunteer.created_at < cutoff,
            ).all()

            count = 0
            for v in candidates:
                # Nicht löschen wenn Volunteer noch zukünftige Dienste hat
                has_future = (
                    Registration.query
                    .join(Shift, Registration.shift_id == Shift.id)
                    .join(EventDate, Shift.event_date_id == EventDate.id)
                    .filter(
                        Registration.volunteer_id == v.id,
                        EventDate.date >= datetime.now(timezone.utc).date(),
                    )
                    .first()
                )
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
    if not _redis_lock(app, 'send_reminders', ttl=86000):
        return
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

            volunteers = Volunteer.query.filter(
                Volunteer.notifications_enabled.is_(True),
                Volunteer.email.isnot(None),
                Volunteer.deleted_at.is_(None),
            ).all()

            for v in volunteers:
                shifts_tomorrow = (
                    Registration.query
                    .join(Shift, Registration.shift_id == Shift.id)
                    .join(EventDate, Shift.event_date_id == EventDate.id)
                    .filter(
                        Registration.volunteer_id == v.id,
                        EventDate.date == tomorrow,
                    )
                    .all()
                )

                food_tomorrow = (
                    FoodDonation.query
                    .join(FoodDonationType, FoodDonation.food_type_id == FoodDonationType.id)
                    .filter(
                        FoodDonation.volunteer_id == v.id,
                        FoodDonationType.delivery_datetime >= tomorrow_start,
                        FoodDonationType.delivery_datetime <= tomorrow_end,
                    )
                    .all()
                )

                if not shifts_tomorrow and not food_tomorrow:
                    continue

                settings = get_site_settings(v.instance_id)
                instance = Instance.query.get(v.instance_id)
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
                              copyright_text=copyright_text, opt_out_url=opt_out_url)
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
    """Täglich 18:00 – Zusammenfassung der heutigen Änderungen an Organisatoren."""
    if not _redis_lock(app, 'organizer_digest', ttl=86000):
        return
    with app.app_context():
        try:
            import pytz
            from ..extensions import db
            from ..models import (
                Organizer, Registration, ActivityLog, FoodDonation,
                Shift, Stand, EventDate, Instance,
            )
            from ..models.instance import organizer_instances as oi_table
            from ..utils.mail import is_mail_configured, send_mail, build_organizer_digest_email, get_effective_logo_for_email
            from ..utils.settings_cache import get_global_settings, get_site_settings

            if not is_mail_configured():
                return

            gs = get_global_settings()
            tz_name = gs.timezone if gs and gs.timezone else 'Europe/Berlin'
            tz = pytz.timezone(tz_name)
            now_local = datetime.now(tz)
            today = now_local.date()
            day_start = tz.localize(datetime(today.year, today.month, today.day, 0, 0, 0)).astimezone(timezone.utc)
            day_end = now_local.astimezone(timezone.utc)

            base_url = app.config.get('FRONTEND_URL', '')
            copyright_text = gs.copyright_text if gs else None
            date_label = today.strftime('%d.%m.%Y')

            organizers = Organizer.query.filter(
                Organizer.notifications_enabled.is_(True),
                Organizer.email.isnot(None),
            ).all()

            for org in organizers:
                for instance in org.instances.all():
                    settings = get_site_settings(instance.id)
                    title = settings.site_title if settings else instance.name
                    primary_color = settings.primary_color if settings else None
                    logo_url = get_effective_logo_for_email(
                        settings.logo_filename if settings else None, base_url
                    )

                    # Neue Anmeldungen heute (durch Volunteers oder Admins)
                    regs_today = (
                        db.session.query(Registration, Shift, Stand)
                        .join(Shift, Registration.shift_id == Shift.id)
                        .join(Stand, Shift.stand_id == Stand.id)
                        .filter(
                            Stand.instance_id == instance.id,
                            Registration.registered_at >= day_start,
                            Registration.registered_at <= day_end,
                        )
                        .all()
                    )

                    # Abmeldungen heute (ActivityLog)
                    cancels_today = ActivityLog.query.filter(
                        ActivityLog.instance_id == instance.id,
                        ActivityLog.event_type == ActivityLog.SHIFT_UNREGISTER,
                        ActivityLog.timestamp >= day_start,
                        ActivityLog.timestamp <= day_end,
                    ).all()

                    # Essensspenden heute
                    foods_today = FoodDonation.query.filter(
                        FoodDonation.instance_id == instance.id,
                        FoodDonation.created_at >= day_start,
                        FoodDonation.created_at <= day_end,
                    ).all()

                    if not regs_today and not cancels_today and not foods_today:
                        continue

                    reg_data = [
                        {
                            'name': (r.volunteer.display_name if r.volunteer else r.guest_name) or '—',
                            'stand': s.name,
                            'time': f'{sh.start_time.strftime("%H:%M")}–{sh.end_time.strftime("%H:%M")}',
                        }
                        for r, sh, s in regs_today
                    ]
                    cancel_data = [
                        {'name': c.volunteer_name or '—', 'stand': '', 'time': c.details or ''}
                        for c in cancels_today
                    ]
                    food_data = [
                        {
                            'name': (f.volunteer.display_name if f.volunteer else f.guest_name) or '—',
                            'food_type': f.food_type.name if f.food_type else '—',
                            'description': f.description,
                        }
                        for f in foods_today
                        if f.food_type
                    ]

                    try:
                        opt_out_url = f'{base_url}/admin/profile'
                        kw = dict(logo_url=logo_url, copyright_text=copyright_text,
                                  opt_out_url=opt_out_url)
                        if primary_color:
                            kw['primary_color'] = primary_color
                        send_mail(
                            org.email,
                            f'Tagesübersicht {date_label} – {title}',
                            build_organizer_digest_email(
                                org.name or org.email,
                                title,
                                date_label,
                                reg_data,
                                cancel_data,
                                food_data,
                                base_url,
                                instance.slug,
                                **kw,
                            ),
                            sender_name=title,
                        )
                        log.info('Organizer-Digest gesendet: organizer_id=%d, instance=%s', org.id, instance.slug)
                    except Exception:
                        log.exception('Organizer-Digest fehlgeschlagen: organizer_id=%d, instance=%s', org.id, instance.slug)

        except Exception:
            log.exception('Organizer-Digest-Job fehlgeschlagen')


def _run_smb_backup(app):
    if not _redis_lock(app, 'smb_backup', ttl=86000):
        return
    with app.app_context():
        try:
            from ..models import GlobalSettings
            gs = GlobalSettings.query.first()
            if not gs or not gs.smb_enabled:
                return
            from ..api.admin.backup import _dump_database, _encrypt_file, _smb_upload
            import os
            import tempfile
            from datetime import timezone

            data = _encrypt_file(_dump_database())
            ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            name = f'standdienst_auto_{ts}.sql.enc'

            with tempfile.NamedTemporaryFile(delete=False, suffix='.enc') as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            try:
                _smb_upload(gs, tmp_path, name)
                log.info('Automatisches SMB-Backup: %s', name)
            finally:
                os.unlink(tmp_path)

        except Exception:
            log.exception('Automatisches SMB-Backup fehlgeschlagen')
