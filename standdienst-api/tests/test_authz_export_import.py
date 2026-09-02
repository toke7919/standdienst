"""Autorisierungstests für app/api/admin/export.py und import_.py.

Beide Dateien: ausschließlich @require_staff (Admin + Organisator, auch
ohne Instanz-Admin-Rechte – lt. CLAUDE.md ausdrücklich so vorgesehen).
Geprüft wird daher nicht Organizer-vs-Instanz-Admin (es gibt hier keinen
Unterschied), sondern Authentifizierung und Instanz-Zugriffsschutz:
ein Organisator ohne Zuweisung zu einer Instanz darf auf deren
Export/Import-Endpunkte nicht zugreifen.
"""
import pytest
from tests.conftest import assign_organizer as _assign, login as _login

EXPORT_GET_ENDPOINTS = [
    '/export/csv/registrations',
    '/export/csv/volunteers',
    '/export/ods/dienste',
    '/export/ods/essen',
    '/export/ods',
    '/export/pdf/dienste',
    '/export/pdf/essen',
    '/export/pdf',
    '/export/ical',
]

IMPORT_TEMPLATE_ENDPOINTS = [
    '/import/template/csv',
    '/import/template/ods',
    '/import/template/xlsx',
]


@pytest.mark.parametrize('path', EXPORT_GET_ENDPOINTS)
def test_export_unauthenticated_rejected(client, instance, path):
    rv = client.get(f'/api/admin/{instance.slug}{path}')
    assert rv.status_code == 401


@pytest.mark.parametrize('path', IMPORT_TEMPLATE_ENDPOINTS)
def test_import_template_unauthenticated_rejected(client, instance, path):
    rv = client.get(f'/api/admin/{instance.slug}{path}')
    assert rv.status_code == 401


def test_import_upload_unauthenticated_rejected(client, instance):
    rv = client.post(f'/api/admin/{instance.slug}/import/shifts/csv')
    assert rv.status_code == 401


@pytest.mark.parametrize('path', EXPORT_GET_ENDPOINTS)
def test_organizer_without_instance_access_rejected(client, instance, other_instance, organizer_user, path):
    _assign(organizer_user, other_instance)  # nur der ANDEREN Instanz zugewiesen
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}{path}')
    assert rv.status_code == 403


def test_organizer_with_instance_access_can_export_csv(client, instance, organizer_user, volunteer):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/export/csv/volunteers')
    assert rv.status_code == 200


def test_organizer_with_instance_access_can_download_import_template(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/import/template/csv')
    assert rv.status_code == 200


def test_organizer_without_instance_access_cannot_import(client, instance, other_instance, organizer_user):
    _assign(organizer_user, other_instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/import/shifts/csv')
    assert rv.status_code == 403
