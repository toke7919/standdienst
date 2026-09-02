"""Autorisierungstests für app/api/admin/stands.py.

list_stands: @require_staff (Organisator darf lesen)
create/update/delete/reorder: @require_instance_admin (einfacher Organisator darf NICHT schreiben)
"""
from app.extensions import db as _db
from app.models import Stand
from tests.conftest import assign_organizer as _assign, login as _login


def _make_stand(instance, name='Teststand'):
    s = Stand(instance_id=instance.id, name=name)
    _db.session.add(s)
    _db.session.commit()
    return s


def test_unauthenticated_rejected(client, instance):
    rv = client.get(f'/api/admin/{instance.slug}/stands')
    assert rv.status_code == 401


def test_organizer_can_list(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/stands')
    assert rv.status_code == 200


def test_organizer_cannot_create(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/stands', json={'name': 'Hack-Stand'})
    assert rv.status_code == 403


def test_organizer_cannot_update(client, instance, organizer_user):
    s = _make_stand(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/stands/{s.id}', json={'name': 'Hack'})
    assert rv.status_code == 403


def test_organizer_cannot_delete(client, instance, organizer_user):
    s = _make_stand(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/stands/{s.id}')
    assert rv.status_code == 403


def test_organizer_cannot_reorder(client, instance, organizer_user):
    s = _make_stand(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/stands/reorder', json={'order': [s.id]})
    assert rv.status_code == 403


def test_instance_admin_can_delete(client, instance, instance_admin_user):
    s = _make_stand(instance)
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/stands/{s.id}')
    assert rv.status_code == 204


def test_instance_admin_cannot_access_stand_of_other_instance(client, instance, other_instance, instance_admin_user):
    foreign_stand = _make_stand(other_instance)
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/stands/{foreign_stand.id}')
    assert rv.status_code == 404
