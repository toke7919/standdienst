"""Autorisierungstests für app/api/admin/organizers.py.

Alle Routen: @require_admin – nur Global-Admins, kein Organizer (auch kein
Instanz-Admin-Organizer) darf andere Organizer verwalten.
"""
from app.extensions import db as _db
from app.models import Organizer
from tests.conftest import login as _login


def _make_organizer(email='foo@test.de'):
    org = Organizer(name='Foo', email=email, is_instance_admin=False)
    org.set_password('TestPass1!')
    _db.session.add(org)
    _db.session.commit()
    return org


def test_unauthenticated_rejected(client):
    rv = client.get('/api/admin/organizers')
    assert rv.status_code == 401


def test_instance_admin_organizer_cannot_list(client, instance_admin_user):
    _login(client, instance_admin_user.email)
    rv = client.get('/api/admin/organizers')
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_create(client, instance_admin_user):
    _login(client, instance_admin_user.email)
    rv = client.post('/api/admin/organizers', json={'email': 'neu@test.de', 'first_name': 'Neu'})
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_update(client, instance_admin_user):
    target = _make_organizer()
    _login(client, instance_admin_user.email)
    rv = client.put(f'/api/admin/organizers/{target.id}', json={'first_name': 'Hack'})
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_delete(client, instance_admin_user):
    target = _make_organizer()
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/organizers/{target.id}')
    assert rv.status_code == 403


def test_global_admin_can_list(client, admin_user):
    _login(client, admin_user.email)
    rv = client.get('/api/admin/organizers')
    assert rv.status_code == 200


def test_global_admin_can_delete(client, admin_user):
    target = _make_organizer()
    _login(client, admin_user.email)
    rv = client.delete(f'/api/admin/organizers/{target.id}')
    assert rv.status_code == 204
