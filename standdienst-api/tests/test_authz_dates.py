"""Autorisierungstests für app/api/admin/dates.py.

list_dates: @require_staff (Organisator darf lesen)
create/update/delete/duplicate: @require_instance_admin (einfacher Organisator darf NICHT schreiben)
"""
from datetime import date as _date
from app.extensions import db as _db
from app.models import EventDate
from tests.conftest import assign_organizer as _assign, login as _login


def _make_date(instance, date=_date(2027, 1, 1)):
    d = EventDate(instance_id=instance.id, date=date)
    _db.session.add(d)
    _db.session.commit()
    return d


def test_unauthenticated_rejected(client, instance):
    rv = client.get(f'/api/admin/{instance.slug}/dates')
    assert rv.status_code == 401


def test_organizer_can_list(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/dates')
    assert rv.status_code == 200


def test_organizer_cannot_create(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/dates', json={'date': '2027-02-01'})
    assert rv.status_code == 403


def test_organizer_cannot_update(client, instance, organizer_user):
    d = _make_date(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/dates/{d.id}', json={'label': 'Hack'})
    assert rv.status_code == 403


def test_organizer_cannot_delete(client, instance, organizer_user):
    d = _make_date(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/dates/{d.id}')
    assert rv.status_code == 403


def test_organizer_cannot_duplicate(client, instance, organizer_user):
    d = _make_date(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/dates/{d.id}/duplicate', json={'date': '2027-03-01'})
    assert rv.status_code == 403


def test_instance_admin_can_create(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/dates', json={'date': '2027-04-01'})
    assert rv.status_code == 201


def test_instance_admin_cannot_access_date_of_other_instance(client, instance, other_instance, instance_admin_user):
    foreign_date = _make_date(other_instance)
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/dates/{foreign_date.id}', json={'label': 'Fremdzugriff'})
    assert rv.status_code == 404
