"""Autorisierungstests für app/api/admin/backup.py.

Alle Routen: @require_admin – Backups sind eine reine Global-Admin-Operation,
kein Organizer (auch kein Instanz-Admin) darf Backups verwalten.
"""
import pytest
from tests.conftest import login as _login

GET_ENDPOINTS = ['/backup/settings', '/backup/list']


@pytest.mark.parametrize('path', GET_ENDPOINTS)
def test_unauthenticated_rejected(client, path):
    rv = client.get(f'/api/admin{path}')
    assert rv.status_code == 401


@pytest.mark.parametrize('path', GET_ENDPOINTS)
def test_instance_admin_organizer_cannot_access(client, instance_admin_user, path):
    _login(client, instance_admin_user.email)
    rv = client.get(f'/api/admin{path}')
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_create_backup(client, instance_admin_user):
    _login(client, instance_admin_user.email)
    rv = client.post('/api/admin/backup/create', json={})
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_delete_backup(client, instance_admin_user):
    _login(client, instance_admin_user.email)
    rv = client.delete('/api/admin/backup/irgendein-name')
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_restore_backup(client, instance_admin_user):
    _login(client, instance_admin_user.email)
    rv = client.post('/api/admin/backup/irgendein-name/restore', json={})
    assert rv.status_code == 403


def test_global_admin_can_list_backups(client, admin_user):
    _login(client, admin_user.email)
    rv = client.get('/api/admin/backup/list')
    assert rv.status_code == 200
