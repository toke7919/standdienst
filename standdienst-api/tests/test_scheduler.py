"""Funktionale Tests für app/utils/scheduler.py – APScheduler-Jobs.

Sicherheitsprüfung vorab (wie bei update.py): Quellcode-Review bestätigt, dass
dieses Modul keine Subprocess-/Netzwerk-Operationen enthält – nur DB-Queries
und E-Mail-Versand. `run_scheduler()` selbst (registriert Cron-Trigger, ruft
_scheduler.start() das BLOCKIERT) wird bewusst NICHT aufgerufen; getestet
werden ausschließlich die einzelnen Job-Funktionen direkt mit dem echten
Flask-`app`-Objekt.

is_mail_configured/send_mail werden in _send_reminders/_send_organizer_digest
lokal pro Funktionsaufruf importiert (`from ..utils.mail import ...`) ->
gemockt wird daher auf app.utils.mail.<name> (Quellmodul), nicht auf
app.utils.scheduler.
"""
from datetime import date, time, datetime, timedelta, timezone
from unittest.mock import patch

from app.extensions import db as _db
from app.models import (
    Admin, Organizer, Volunteer, ActivityLog, GlobalSettings,
    Stand, EventDate, Shift, Registration, FoodDonationType, FoodDonation,
)
from app.models.instance import organizer_instances, admin_digest_subscriptions
from app.utils.scheduler import (
    _purge_expired_tokens, _purge_old_logs, _purge_old_volunteers,
    _send_reminders, _send_organizer_digest,
)


# ---------------------------------------------------------------------------
# _purge_expired_tokens
# ---------------------------------------------------------------------------

def test_purge_expired_tokens_clears_expired_and_keeps_valid(app, instance):
    admin = Admin(email='expired-admin@test.de', is_primary=True)
    admin.set_password('SicheresPass1!')
    admin.reset_token = 'abc'
    admin.reset_token_expires = datetime.now(timezone.utc) - timedelta(hours=1)
    _db.session.add(admin)

    volunteer = Volunteer(instance_id=instance.id, name='Gültig', first_name='Gültig')
    volunteer.set_password('TestPass1!')
    volunteer.reset_token = 'xyz'
    volunteer.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    _db.session.add(volunteer)
    _db.session.commit()

    _purge_expired_tokens(app)

    _db.session.refresh(admin)
    _db.session.refresh(volunteer)
    assert admin.reset_token is None
    assert volunteer.reset_token == 'xyz'  # noch gültig, unangetastet


# ---------------------------------------------------------------------------
# _purge_old_logs
# ---------------------------------------------------------------------------

def test_purge_old_logs_deletes_only_entries_older_than_retention(app, instance):
    old_log = ActivityLog(
        instance_id=instance.id, event_type=ActivityLog.AUDIT_DATA,
        volunteer_name='Alt', actor_type='admin', details='alt',
    )
    _db.session.add(old_log)
    _db.session.commit()
    old_log.timestamp = datetime.now(timezone.utc) - timedelta(days=200)
    new_log = ActivityLog(
        instance_id=instance.id, event_type=ActivityLog.AUDIT_DATA,
        volunteer_name='Neu', actor_type='admin', details='neu',
    )
    _db.session.add(new_log)
    _db.session.commit()

    _purge_old_logs(app)  # kein GlobalSettings -> Default 3 Monate (~90 Tage)

    remaining = _db.session.query(ActivityLog).all()
    assert len(remaining) == 1
    assert remaining[0].details == 'neu'


def test_purge_old_logs_respects_configured_retention(app, instance):
    gs = GlobalSettings(log_retention_months=12)
    _db.session.add(gs)
    log = ActivityLog(
        instance_id=instance.id, event_type=ActivityLog.AUDIT_DATA,
        volunteer_name='X', actor_type='admin', details='x',
    )
    _db.session.add(log)
    _db.session.commit()
    log.timestamp = datetime.now(timezone.utc) - timedelta(days=200)  # < 12 Monate
    _db.session.commit()

    _purge_old_logs(app)

    assert _db.session.query(ActivityLog).count() == 1  # noch innerhalb 12 Monate


# ---------------------------------------------------------------------------
# _purge_old_volunteers
# ---------------------------------------------------------------------------

def test_purge_old_volunteers_noop_without_retention_setting(app, instance):
    v = Volunteer(instance_id=instance.id, name='Alt', first_name='Alt')
    _db.session.add(v)
    _db.session.commit()
    v.created_at = datetime.now(timezone.utc) - timedelta(days=1000)
    _db.session.commit()

    _purge_old_volunteers(app)  # kein GlobalSettings -> No-Op

    _db.session.refresh(v)
    assert v.deleted_at is None


def test_purge_old_volunteers_soft_deletes_eligible_and_skips_future_shift(app, instance):
    gs = GlobalSettings(volunteer_retention_months=6)
    _db.session.add(gs)

    old_no_future = Volunteer(instance_id=instance.id, name='Löschbar', first_name='Löschbar')
    old_with_future = Volunteer(instance_id=instance.id, name='Zukunft', first_name='Zukunft')
    recent = Volunteer(instance_id=instance.id, name='Frisch', first_name='Frisch')
    _db.session.add_all([old_no_future, old_with_future, recent])
    _db.session.commit()

    old_cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    old_no_future.created_at = old_cutoff
    old_with_future.created_at = old_cutoff
    recent.created_at = datetime.now(timezone.utc)  # nicht alt genug
    _db.session.commit()

    stand = Stand(instance_id=instance.id, name='Stand')
    _db.session.add(stand)
    _db.session.flush()
    future_date = EventDate(instance_id=instance.id, date=date.today() + timedelta(days=30), is_draft=False)
    _db.session.add(future_date)
    _db.session.flush()
    future_shift = Shift(stand_id=stand.id, event_date_id=future_date.id,
                         start_time=time(10, 0), end_time=time(12, 0))
    _db.session.add(future_shift)
    _db.session.flush()
    _db.session.add(Registration(volunteer_id=old_with_future.id, shift_id=future_shift.id))
    _db.session.commit()

    _purge_old_volunteers(app)

    _db.session.refresh(old_no_future)
    _db.session.refresh(old_with_future)
    _db.session.refresh(recent)
    assert old_no_future.deleted_at is not None
    assert old_with_future.deleted_at is None  # hat noch einen zukünftigen Dienst
    assert recent.deleted_at is None  # noch nicht alt genug


def test_purge_old_volunteers_skips_already_deleted(app, instance):
    gs = GlobalSettings(volunteer_retention_months=6)
    _db.session.add(gs)
    v = Volunteer(instance_id=instance.id, name='Schon Weg', first_name='Schon')
    _db.session.add(v)
    _db.session.commit()
    v.created_at = datetime.now(timezone.utc) - timedelta(days=365)
    v.soft_delete()
    _db.session.commit()
    deleted_at_before = v.deleted_at

    _purge_old_volunteers(app)

    _db.session.refresh(v)
    assert v.deleted_at == deleted_at_before  # unverändert, kein erneuter Zugriff


# ---------------------------------------------------------------------------
# _send_reminders
# ---------------------------------------------------------------------------

def _make_shift_tomorrow(instance):
    stand = Stand(instance_id=instance.id, name='Kasse')
    _db.session.add(stand)
    _db.session.flush()
    ed = EventDate(instance_id=instance.id, date=date.today() + timedelta(days=1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    shift = Shift(stand_id=stand.id, event_date_id=ed.id, start_time=time(10, 0), end_time=time(12, 0))
    _db.session.add(shift)
    _db.session.commit()
    return shift


@patch('app.utils.mail.is_mail_configured', return_value=False)
def test_send_reminders_noop_when_mail_not_configured(mock_configured, app, instance, volunteer):
    volunteer.notifications_enabled = True
    _db.session.commit()
    with patch('app.utils.mail.send_mail') as mock_send:
        _send_reminders(app)
        mock_send.assert_not_called()


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_reminders_sends_for_shift_tomorrow(mock_configured, mock_send, app, instance, volunteer):
    volunteer.notifications_enabled = True
    _db.session.commit()
    shift = _make_shift_tomorrow(instance)
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    _send_reminders(app)

    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == volunteer.email


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_reminders_uses_instance_primary_color(mock_configured, mock_send, app, instance, volunteer):
    from app.models import SiteSettings
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.primary_color = '#123456'
    volunteer.notifications_enabled = True
    _db.session.commit()
    shift = _make_shift_tomorrow(instance)
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    _send_reminders(app)
    mock_send.assert_called_once()


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_reminders_skips_volunteer_without_activity_tomorrow(mock_configured, mock_send, app, instance, volunteer):
    volunteer.notifications_enabled = True
    _db.session.commit()
    _send_reminders(app)
    mock_send.assert_not_called()


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_reminders_excludes_volunteers_with_notifications_disabled(mock_configured, mock_send, app, instance, volunteer):
    volunteer.notifications_enabled = False
    _db.session.commit()
    shift = _make_shift_tomorrow(instance)
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    _send_reminders(app)
    mock_send.assert_not_called()


@patch('app.utils.mail.send_mail', side_effect=RuntimeError('SMTP down'))
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_reminders_one_failure_does_not_stop_job(mock_configured, mock_send, app, instance, volunteer):
    volunteer.notifications_enabled = True
    _db.session.commit()
    shift = _make_shift_tomorrow(instance)
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    _send_reminders(app)  # darf nicht raisen
    mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# _send_organizer_digest
# ---------------------------------------------------------------------------

def _make_registration_yesterday(instance, volunteer):
    stand = Stand(instance_id=instance.id, name='Kasse')
    _db.session.add(stand)
    _db.session.flush()
    ed = EventDate(instance_id=instance.id, date=date.today() - timedelta(days=1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    shift = Shift(stand_id=stand.id, event_date_id=ed.id, start_time=time(10, 0), end_time=time(12, 0))
    _db.session.add(shift)
    _db.session.flush()
    reg = Registration(volunteer_id=volunteer.id, shift_id=shift.id)
    _db.session.add(reg)
    _db.session.commit()
    reg.registered_at = datetime.now(timezone.utc) - timedelta(days=1)
    _db.session.commit()
    return reg


@patch('app.utils.mail.is_mail_configured', return_value=False)
def test_send_organizer_digest_noop_when_mail_not_configured(mock_configured, app, instance, organizer_user, volunteer):
    from tests.conftest import assign_organizer
    assign_organizer(organizer_user, instance)
    _make_registration_yesterday(instance, volunteer)
    with patch('app.utils.mail.send_mail') as mock_send:
        _send_organizer_digest(app)
        mock_send.assert_not_called()


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_organizer_digest_sends_when_activity_present(mock_configured, mock_send, app, instance, organizer_user, volunteer):
    from tests.conftest import assign_organizer
    assign_organizer(organizer_user, instance)
    _make_registration_yesterday(instance, volunteer)

    _send_organizer_digest(app)

    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == organizer_user.email


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_organizer_digest_skips_organizer_without_activity(mock_configured, mock_send, app, instance, organizer_user):
    from tests.conftest import assign_organizer
    assign_organizer(organizer_user, instance)
    _send_organizer_digest(app)
    mock_send.assert_not_called()


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_organizer_digest_skips_organizer_with_digest_disabled(mock_configured, mock_send, app, instance, organizer_user, volunteer):
    _db.session.execute(organizer_instances.insert().values(
        organizer_id=organizer_user.id, instance_id=instance.id,
        is_primary=False, is_instance_admin=False, digest_enabled=False,
    ))
    _db.session.commit()
    _make_registration_yesterday(instance, volunteer)

    _send_organizer_digest(app)
    mock_send.assert_not_called()


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_organizer_digest_sends_to_subscribed_admin(mock_configured, mock_send, app, instance, admin_user, volunteer):
    _db.session.execute(admin_digest_subscriptions.insert().values(
        admin_id=admin_user.id, instance_id=instance.id,
    ))
    _db.session.commit()
    _make_registration_yesterday(instance, volunteer)

    _send_organizer_digest(app)

    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == admin_user.email


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_organizer_digest_admin_without_subscription_receives_nothing(mock_configured, mock_send, app, instance, admin_user, volunteer):
    _make_registration_yesterday(instance, volunteer)
    _send_organizer_digest(app)
    mock_send.assert_not_called()


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_organizer_digest_subscribed_admin_without_activity_receives_nothing(mock_configured, mock_send, app, instance, admin_user):
    _db.session.execute(admin_digest_subscriptions.insert().values(
        admin_id=admin_user.id, instance_id=instance.id,
    ))
    _db.session.commit()
    _send_organizer_digest(app)
    mock_send.assert_not_called()


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_organizer_digest_uses_instance_primary_color(mock_configured, mock_send, app, instance, organizer_user, volunteer):
    from app.models import SiteSettings
    from tests.conftest import assign_organizer
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.primary_color = '#654321'
    _db.session.commit()
    assign_organizer(organizer_user, instance)
    _make_registration_yesterday(instance, volunteer)

    _send_organizer_digest(app)
    mock_send.assert_called_once()


@patch('app.utils.mail.send_mail', side_effect=RuntimeError('SMTP down'))
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_send_organizer_digest_failure_does_not_stop_job(mock_configured, mock_send, app, instance, organizer_user, volunteer):
    from tests.conftest import assign_organizer
    assign_organizer(organizer_user, instance)
    _make_registration_yesterday(instance, volunteer)

    _send_organizer_digest(app)  # darf nicht raisen
    mock_send.assert_called_once()
