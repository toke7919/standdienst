"""Autorisierungstests für app/api/admin/instances.py.

list_instances: @require_staff, aber datenscopiert (Organizer sieht nur eigene Instanzen).
create/get/update/delete: @require_admin (nur Global-Admin).
clear_instance_data: @require_staff + zusätzliche Inline-Prüfung (nur g.role == 'admin').
"""
from tests.conftest import assign_organizer as _assign, login as _login


def test_unauthenticated_rejected(client):
    rv = client.get('/api/admin/instances')
    assert rv.status_code == 401


def test_organizer_sees_only_assigned_instances(client, instance, other_instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get('/api/admin/instances')
    assert rv.status_code == 200
    slugs = [i['slug'] for i in rv.get_json()['data']]
    assert instance.slug in slugs
    assert other_instance.slug not in slugs


def test_organizer_cannot_create_instance(client, organizer_user):
    _login(client, organizer_user.email)
    rv = client.post('/api/admin/instances', json={'slug': 'neu', 'name': 'Neu'})
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_update_instance(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.put(f'/api/admin/instances/{instance.id}', json={'name': 'Hack'})
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_delete_instance(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/instances/{instance.id}')
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_clear_instance_data(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/clear-data')
    assert rv.status_code == 403


def test_global_admin_can_create_instance(client, admin_user):
    _login(client, admin_user.email)
    rv = client.post('/api/admin/instances', json={'slug': 'neu-instanz', 'name': 'Neu'})
    assert rv.status_code == 201


def test_global_admin_can_clear_instance_data(client, instance, admin_user):
    _login(client, admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/clear-data')
    assert rv.status_code == 204
