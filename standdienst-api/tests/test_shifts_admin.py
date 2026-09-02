"""Funktionale Tests für app/api/admin/shifts.py.

Autorisierung (@require_staff/@require_instance_admin, Instanz-Zugriffsschutz)
ist bereits in test_authz_shifts.py abgedeckt. Hier geht es um Filter,
Validierung (Zeit-Reihenfolge, Duplikat-Schutz), Optimistic Locking und
Aktivitätslog-Details.
"""
from datetime import date, time, datetime, timezone, timedelta

from app.extensions import db as _db
from app.models import Stand, EventDate, Shift, ActivityLog
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


def _make_stand(instance, name='Stand'):
    stand = Stand(instance_id=instance.id, name=name)
    _db.session.add(stand)
    _db.session.commit()
    return stand


def _make_event_date(instance, day=date(2026, 9, 1)):
    ed = _db.session.query(EventDate).filter_by(instance_id=instance.id, date=day).first()
    if not ed:
        ed = EventDate(instance_id=instance.id, date=day, is_draft=False)
        _db.session.add(ed)
        _db.session.commit()
    return ed


def _make_shift(instance, stand=None, ed=None, start=time(10, 0), end=time(12, 0), max_volunteers=2):
    stand = stand or _make_stand(instance)
    ed = ed or _make_event_date(instance)
    shift = Shift(stand_id=stand.id, event_date_id=ed.id, start_time=start, end_time=end,
                  max_volunteers=max_volunteers)
    _db.session.add(shift)
    _db.session.commit()
    return shift


# ---------------------------------------------------------------------------
# GET /shifts
# ---------------------------------------------------------------------------

def test_list_shifts_filters_by_date_id_and_stand_id(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    stand_a = _make_stand(instance, 'A')
    stand_b = _make_stand(instance, 'B')
    ed1 = _make_event_date(instance, date(2026, 9, 1))
    ed2 = _make_event_date(instance, date(2026, 9, 2))
    _make_shift(instance, stand_a, ed1)
    _make_shift(instance, stand_b, ed1)
    _make_shift(instance, stand_a, ed2)

    rv = c.get(f'/api/admin/{instance.slug}/shifts?date_id={ed1.id}&stand_id={stand_a.id}')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert len(data) == 1
    assert data[0]['stand_id'] == stand_a.id
    assert data[0]['event_date_id'] == ed1.id


# ---------------------------------------------------------------------------
# POST /shifts
# ---------------------------------------------------------------------------

def test_create_shift_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/shifts', json={})
    assert rv.status_code == 422


def test_create_shift_start_after_end_returns_400(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    stand = _make_stand(instance)
    ed = _make_event_date(instance)
    rv = c.post(f'/api/admin/{instance.slug}/shifts', json={
        'stand_id': stand.id, 'event_date_id': ed.id,
        'start_time': '14:00', 'end_time': '10:00',
    })
    assert rv.status_code == 400


def test_create_shift_stand_or_date_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    stand = _make_stand(instance)
    rv = c.post(f'/api/admin/{instance.slug}/shifts', json={
        'stand_id': stand.id, 'event_date_id': 99999,
        'start_time': '10:00', 'end_time': '12:00',
    })
    assert rv.status_code == 404


def test_create_shift_success_logs_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    stand = _make_stand(instance)
    ed = _make_event_date(instance)
    rv = c.post(f'/api/admin/{instance.slug}/shifts', json={
        'stand_id': stand.id, 'event_date_id': ed.id,
        'start_time': '10:00', 'end_time': '12:00', 'max_volunteers': 3,
    })
    assert rv.status_code == 201
    data = rv.get_json()['data']
    assert data['max_volunteers'] == 3

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Dienst angelegt' in log.details


def test_create_shift_duplicate_returns_409(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    stand = _make_stand(instance)
    ed = _make_event_date(instance)
    _make_shift(instance, stand, ed, start=time(10, 0), end=time(12, 0))

    rv = c.post(f'/api/admin/{instance.slug}/shifts', json={
        'stand_id': stand.id, 'event_date_id': ed.id,
        'start_time': '10:00', 'end_time': '12:00',
    })
    assert rv.status_code == 409


# ---------------------------------------------------------------------------
# PUT /shifts/<id>
# ---------------------------------------------------------------------------

def test_update_shift_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/shifts/99999', json={'max_volunteers': 5})
    assert rv.status_code == 404


def test_update_shift_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance)
    rv = c.put(f'/api/admin/{instance.slug}/shifts/{shift.id}', json={'max_volunteers': 0})
    assert rv.status_code == 422


def test_update_shift_start_after_end_returns_400(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance, start=time(10, 0), end=time(12, 0))
    rv = c.put(f'/api/admin/{instance.slug}/shifts/{shift.id}', json={'start_time': '13:00'})
    assert rv.status_code == 400


def test_update_shift_optimistic_lock_conflict(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance)
    stale = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rv = c.put(f'/api/admin/{instance.slug}/shifts/{shift.id}', json={
        'max_volunteers': 5, 'updated_at': stale,
    })
    assert rv.status_code == 409


def test_update_shift_success_logs_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance)
    rv = c.put(f'/api/admin/{instance.slug}/shifts/{shift.id}', json={'max_volunteers': 7})
    assert rv.status_code == 200
    assert rv.get_json()['data']['max_volunteers'] == 7

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Dienst geändert' in log.details


# ---------------------------------------------------------------------------
# DELETE /shifts/<id>
# ---------------------------------------------------------------------------

def test_delete_shift_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.delete(f'/api/admin/{instance.slug}/shifts/99999')
    assert rv.status_code == 404


def test_delete_shift_success_logs_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance)
    shift_id = shift.id
    rv = c.delete(f'/api/admin/{instance.slug}/shifts/{shift_id}')
    assert rv.status_code == 204
    assert _db.session.get(Shift, shift_id) is None

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Dienst gelöscht' in log.details
