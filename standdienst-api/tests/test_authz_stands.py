"""Autorisierungstests für app/api/admin/stands.py.

list_stands: @require_staff (Organisator darf lesen)
create/update/delete/reorder: @require_staff (Organisator darf schreiben, nur eigene Instanz)
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


def test_organizer_can_create(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/stands', json={'name': 'Neuer Stand'})
    assert rv.status_code == 201


def test_organizer_can_update(client, instance, organizer_user):
    s = _make_stand(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/stands/{s.id}', json={'name': 'Umbenannt', 'updated_at': s.updated_at.isoformat()})
    assert rv.status_code == 200
    assert rv.get_json()['data']['name'] == 'Umbenannt'


def test_organizer_can_delete(client, instance, organizer_user):
    s = _make_stand(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/stands/{s.id}')
    assert rv.status_code == 204


def test_organizer_can_reorder(client, instance, organizer_user):
    s = _make_stand(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/stands/reorder', json={'order': [s.id]})
    assert rv.status_code == 200


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


def test_organizer_of_other_instance_cannot_create(client, instance, other_instance, organizer_user):
    _assign(organizer_user, other_instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/stands', json={'name': 'Fremd'})
    assert rv.status_code == 403


def test_organizer_cannot_access_stand_of_other_instance(client, instance, other_instance, organizer_user):
    foreign_stand = _make_stand(other_instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/stands/{foreign_stand.id}')
    assert rv.status_code == 404
