"""Autorisierungstests für app/api/admin/update.py.

Alle Routen: @require_admin – Update-Prüfung/-Anwendung ist eine reine
Global-Admin-Operation.
"""
from tests.conftest import login as _login


def test_unauthenticated_rejected(client):
    rv = client.get('/api/admin/update/check')
    assert rv.status_code == 401


def test_instance_admin_organizer_cannot_check_update(client, instance_admin_user):
    _login(client, instance_admin_user.email)
    rv = client.get('/api/admin/update/check')
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_apply_update(client, instance_admin_user):
    _login(client, instance_admin_user.email)
    rv = client.post('/api/admin/update/apply', json={})
    assert rv.status_code == 403
