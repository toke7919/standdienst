"""Autorisierungstests für app/api/admin/admins.py.

Alle Routen: @require_admin – nur Global-Admins, kein Organizer darf
andere Admin-Konten verwalten.
"""
from app.extensions import db as _db
from app.models import Admin
from tests.conftest import login as _login


def _make_admin(email='second@test.de'):
    a = Admin(email=email, is_primary=False)
    a.set_password('TestPass1!')
    _db.session.add(a)
    _db.session.commit()
    return a


def test_unauthenticated_rejected(client):
    rv = client.get('/api/admin/admins')
    assert rv.status_code == 401


def test_instance_admin_organizer_cannot_list(client, instance_admin_user):
    _login(client, instance_admin_user.email)
    rv = client.get('/api/admin/admins')
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_create(client, instance_admin_user):
    _login(client, instance_admin_user.email)
    rv = client.post('/api/admin/admins', json={
        'email': 'hack@test.de', 'password': 'StrongPass1!',
    })
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_update(client, instance_admin_user):
    target = _make_admin()
    _login(client, instance_admin_user.email)
    rv = client.put(f'/api/admin/admins/{target.id}', json={'first_name': 'Hack'})
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_delete(client, instance_admin_user):
    target = _make_admin()
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/admins/{target.id}')
    assert rv.status_code == 403


def test_global_admin_can_list(client, admin_user):
    _login(client, admin_user.email)
    rv = client.get('/api/admin/admins')
    assert rv.status_code == 200


def test_global_admin_can_delete_non_primary_non_self(client, admin_user):
    target = _make_admin()
    _login(client, admin_user.email)
    rv = client.delete(f'/api/admin/admins/{target.id}')
    assert rv.status_code == 204
