"""Autorisierungstests für app/api/admin/dsgvo.py.

@require_instance_admin – WICHTIG: strenger als require_staff, ein
einfacher Organisator darf das DSGVO-Verarbeitungsverzeichnis (Art. 30)
seiner eigenen Instanz NICHT einsehen.
"""
from tests.conftest import assign_organizer as _assign, login as _login


def test_unauthenticated_rejected(client, instance):
    rv = client.get(f'/api/admin/{instance.slug}/dsgvo/processing-record')
    assert rv.status_code == 401


def test_plain_organizer_cannot_access(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/dsgvo/processing-record')
    assert rv.status_code == 403


def test_instance_admin_organizer_can_access_own_instance(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/dsgvo/processing-record')
    assert rv.status_code == 200


def test_instance_admin_cannot_access_other_instance(client, instance, other_instance, instance_admin_user):
    _assign(instance_admin_user, other_instance)
    _login(client, instance_admin_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/dsgvo/processing-record')
    assert rv.status_code == 403
