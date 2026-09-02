"""Autorisierungstests für app/api/admin/activity.py.

/activity (global): @require_admin (nur Global-Admin)
/<slug>/activity (Instanz): @require_instance_admin – WICHTIG: strenger als
require_staff, ein einfacher Organisator (ohne Instanz-Admin-Rechte) darf
das Aktivitätsprotokoll seiner eigenen Instanz NICHT einsehen.
"""
from tests.conftest import assign_organizer as _assign, login as _login


def test_global_activity_unauthenticated_rejected(client):
    rv = client.get('/api/admin/activity')
    assert rv.status_code == 401


def test_instance_activity_unauthenticated_rejected(client, instance):
    rv = client.get(f'/api/admin/{instance.slug}/activity')
    assert rv.status_code == 401


def test_instance_admin_organizer_cannot_view_global_activity(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.get('/api/admin/activity')
    assert rv.status_code == 403


def test_global_admin_can_view_global_activity(client, admin_user):
    _login(client, admin_user.email)
    rv = client.get('/api/admin/activity')
    assert rv.status_code == 200


def test_plain_organizer_cannot_view_instance_activity(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/activity')
    assert rv.status_code == 403


def test_instance_admin_organizer_can_view_own_instance_activity(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/activity')
    assert rv.status_code == 200


def test_instance_admin_cannot_view_activity_of_other_instance(client, instance, other_instance, instance_admin_user):
    _assign(instance_admin_user, other_instance)
    _login(client, instance_admin_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/activity')
    assert rv.status_code == 403
