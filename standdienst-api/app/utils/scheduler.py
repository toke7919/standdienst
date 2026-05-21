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
                # Nicht löschen wenn Volunteer noch zukünftige Schichten hat
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
            from ..utils.mail import is_mail_configured, send_mail, build_reminder_email
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
                primary_color = settings.primary_color if settings else '#4f46e5'
                logo_url = (
                    f'{base_url}/uploads/{settings.logo_filename}'
                    if settings and settings.logo_filename else None
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
                    send_mail(
                        v.email,
                        f'Erinnerung für morgen – {title}',
                        build_reminder_email(v.name, shift_data, food_data, title, base_url,
                                             slug=slug, primary_color=primary_color,
                                             logo_url=logo_url, copyright_text=copyright_text),
                        sender_name=title,
                    )
                    log.info('Erinnerungsmail gesendet: volunteer_id=%d', v.id)
                except Exception:
                    log.exception('Erinnerungsmail fehlgeschlagen: volunteer_id=%d', v.id)

        except Exception:
            log.exception('Erinnerungs-Job fehlgeschlagen')


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
