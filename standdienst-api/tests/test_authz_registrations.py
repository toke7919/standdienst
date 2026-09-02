"""Autorisierungstests für app/api/admin/registrations.py.

list/grid: @require_staff (Organisator darf lesen)
create/delete: @require_instance_admin (einfacher Organisator darf NICHT schreiben)
"""
from datetime import date as _date, time as _time
from app.extensions import db as _db
from app.models import EventDate, Registration, Shift, Stand
from tests.conftest import assign_organizer as _assign, login as _login


def _make_shift(instance):
    stand = Stand(instance_id=instance.id, name='Stand')
    d = EventDate(instance_id=instance.id, date=_date(2027, 1, 1))
    _db.session.add_all([stand, d])
    _db.session.commit()
    shift = Shift(
        stand_id=stand.id, event_date_id=d.id,
        start_time=_time(8, 0), end_time=_time(12, 0), max_volunteers=2,
    )
    _db.session.add(shift)
    _db.session.commit()
    return shift


def _make_registration(instance, shift=None):
    shift = shift or _make_shift(instance)
    reg = Registration(shift_id=shift.id, guest_name='Gast', registered_by_admin=True)
    _db.session.add(reg)
    _db.session.commit()
    return reg


def test_unauthenticated_rejected(client, instance):
    rv = client.get(f'/api/admin/{instance.slug}/registrations')
    assert rv.status_code == 401


def test_organizer_can_list(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/registrations')
    assert rv.status_code == 200


def test_organizer_can_view_grid(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/registrations/grid')
    assert rv.status_code == 200


def test_organizer_cannot_create(client, instance, organizer_user):
    shift = _make_shift(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/registrations', json={
        'shift_id': shift.id, 'guest_name': 'Hack',
    })
    assert rv.status_code == 403


def test_organizer_cannot_delete(client, instance, organizer_user):
    reg = _make_registration(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/registrations/{reg.id}')
    assert rv.status_code == 403


def test_instance_admin_can_create(client, instance, instance_admin_user):
    shift = _make_shift(instance)
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/registrations', json={
        'shift_id': shift.id, 'guest_name': 'Gast',
    })
    assert rv.status_code == 201


def test_instance_admin_cannot_access_registration_of_other_instance(client, instance, other_instance, instance_admin_user):
    foreign_reg = _make_registration(other_instance)
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/registrations/{foreign_reg.id}')
    assert rv.status_code == 404
