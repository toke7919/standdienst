"""Autorisierungstests für app/api/admin/shifts.py.

list_shifts: @require_staff (Organisator darf lesen)
create/update/delete: @require_instance_admin (einfacher Organisator darf NICHT schreiben)
"""
from datetime import date as _date, time as _time
from app.extensions import db as _db
from app.models import EventDate, Shift, Stand
from tests.conftest import assign_organizer as _assign, login as _login


def _make_stand(instance, name='Teststand'):
    s = Stand(instance_id=instance.id, name=name)
    _db.session.add(s)
    _db.session.commit()
    return s


def _make_shift(instance, stand=None, event_date=None, start='08:00', end='12:00'):
    stand = stand or _make_stand(instance)
    event_date = event_date or EventDate(instance_id=instance.id, date=_date(2027, 1, 1))
    if event_date.id is None:
        _db.session.add(event_date)
        _db.session.commit()
    shift = Shift(
        stand_id=stand.id, event_date_id=event_date.id,
        start_time=_time.fromisoformat(start), end_time=_time.fromisoformat(end),
        max_volunteers=2,
    )
    _db.session.add(shift)
    _db.session.commit()
    return shift


def test_unauthenticated_rejected(client, instance):
    rv = client.get(f'/api/admin/{instance.slug}/shifts')
    assert rv.status_code == 401


def test_organizer_can_list(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/shifts')
    assert rv.status_code == 200


def test_organizer_cannot_create(client, instance, organizer_user):
    stand = _make_stand(instance)
    d = EventDate(instance_id=instance.id, date=_date(2027, 1, 1))
    _db.session.add(d)
    _db.session.commit()
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/shifts', json={
        'stand_id': stand.id, 'event_date_id': d.id,
        'start_time': '08:00', 'end_time': '12:00', 'max_volunteers': 2,
    })
    assert rv.status_code == 403


def test_organizer_cannot_update(client, instance, organizer_user):
    shift = _make_shift(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/shifts/{shift.id}', json={'max_volunteers': 5})
    assert rv.status_code == 403


def test_organizer_cannot_delete(client, instance, organizer_user):
    shift = _make_shift(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/shifts/{shift.id}')
    assert rv.status_code == 403


def test_instance_admin_can_delete(client, instance, instance_admin_user):
    shift = _make_shift(instance)
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/shifts/{shift.id}')
    assert rv.status_code == 204


def test_instance_admin_cannot_access_shift_of_other_instance(client, instance, other_instance, instance_admin_user):
    foreign_shift = _make_shift(other_instance)
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/shifts/{foreign_shift.id}')
    assert rv.status_code == 404
