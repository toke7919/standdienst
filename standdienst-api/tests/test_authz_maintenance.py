"""Autorisierungstests für app/api/admin/maintenance.py.

@require_admin – Wartungsmodus ist eine reine Global-Admin-Operation.
"""
from app.extensions import db as _db
from app.models import GlobalSettings
from tests.conftest import login as _login


def test_unauthenticated_rejected(client):
    rv = client.put('/api/admin/maintenance', json={'enabled': True})
    assert rv.status_code == 401


def test_instance_admin_organizer_cannot_toggle_maintenance(client, instance_admin_user):
    _login(client, instance_admin_user.email)
    rv = client.put('/api/admin/maintenance', json={'enabled': True})
    assert rv.status_code == 403


def test_global_admin_can_toggle_maintenance(client, admin_user):
    _db.session.add(GlobalSettings())
    _db.session.commit()
    _login(client, admin_user.email)
    rv = client.put('/api/admin/maintenance', json={'enabled': True})
    assert rv.status_code == 200
    # Wieder ausschalten, um Seiteneffekte auf andere Tests zu vermeiden
    client.put('/api/admin/maintenance', json={'enabled': False})
