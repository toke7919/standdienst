"""Autorisierungstests für app/api/admin/dashboard.py.

/<slug>/dashboard: @require_staff (Organisator darf lesen)
/dashboard/global: @require_admin (nur Global-Admin, aggregiert instanzübergreifend)
"""
from tests.conftest import assign_organizer as _assign, login as _login


def test_instance_dashboard_unauthenticated_rejected(client, instance):
    rv = client.get(f'/api/admin/{instance.slug}/dashboard')
    assert rv.status_code == 401


def test_global_dashboard_unauthenticated_rejected(client):
    rv = client.get('/api/admin/dashboard/global')
    assert rv.status_code == 401


def test_organizer_can_view_instance_dashboard(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/dashboard')
    assert rv.status_code == 200


def test_organizer_without_instance_access_cannot_view_dashboard(client, instance, other_instance, organizer_user):
    _assign(organizer_user, other_instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/dashboard')
    assert rv.status_code == 403


def test_instance_admin_organizer_cannot_view_global_dashboard(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.get('/api/admin/dashboard/global')
    assert rv.status_code == 403


def test_global_admin_can_view_global_dashboard(client, admin_user):
    _login(client, admin_user.email)
    rv = client.get('/api/admin/dashboard/global')
    assert rv.status_code == 200
