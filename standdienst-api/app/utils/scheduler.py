from datetime import datetime, timedelta, timezone
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)
_scheduler = BackgroundScheduler(timezone='Europe/Berlin')


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

    _scheduler.start()
    log.info('APScheduler gestartet')


def _purge_expired_tokens(app):
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


def _run_smb_backup(app):
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
