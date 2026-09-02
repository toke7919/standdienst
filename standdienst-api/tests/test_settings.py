"""Funktionale Tests für app/api/admin/settings.py.

Grundlegende Autorisierung für /<slug>/settings ist bereits in test_roles.py
abgedeckt. Hier geht es um Geschäftslogik: HTML-Sanitizing, Optimistic Locking,
Logo-Upload (echte Pillow-Bildverarbeitung, aber in ein Temp-Verzeichnis statt
ins echte uploads/), Global-/Mail-Settings-Erstauslegung (Auto-Create) und die
Testmail-Endpunkte (send_mail/is_mail_configured gemockt).

settings.py importiert send_mail/is_mail_configured/apply_db_mail_config auf
Modulebene -> gemockt wird auf app.api.admin.settings.<name>.
"""
import io
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from PIL import Image

from app.extensions import db as _db
from app.models import SiteSettings, GlobalSettings, MailSettings, ActivityLog
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


@pytest.fixture
def temp_upload_dir(app):
    """Verhindert, dass Logo-Upload-Tests echte Dateien in standdienst-api/uploads/ schreiben."""
    with tempfile.TemporaryDirectory() as tmp:
        old = app.config.get('UPLOAD_FOLDER')
        app.config['UPLOAD_FOLDER'] = tmp
        yield tmp
        app.config['UPLOAD_FOLDER'] = old


def _png_bytes(fmt='PNG'):
    buf = io.BytesIO()
    Image.new('RGB', (2, 2), color='red').save(buf, format=fmt)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Site Settings – PUT
# ---------------------------------------------------------------------------

def test_update_site_settings_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/settings', json={'primary_color': 'keine-hex-farbe'})
    assert rv.status_code == 422


def test_update_site_settings_sanitizes_html(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/settings', json={
        'instance_impressum_html': '<p>Text</p><script>alert(1)</script>',
    })
    assert rv.status_code == 200
    html = rv.get_json()['data']['instance_impressum_html']
    assert '<script>' not in html
    assert '<p>Text</p>' in html


def test_update_site_settings_empty_primary_color_becomes_none(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/settings', json={'primary_color': ''})
    assert rv.status_code == 200
    assert rv.get_json()['data']['primary_color'] is None


def test_update_site_settings_optimistic_lock_conflict(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    stale = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.updated_at = datetime.now(timezone.utc)
    _db.session.commit()

    rv = c.put(f'/api/admin/{instance.slug}/settings', json={
        'site_title': 'Zu spät', 'updated_at': stale,
    })
    assert rv.status_code == 409


def test_update_site_settings_activity_log_written(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    c.put(f'/api/admin/{instance.slug}/settings', json={'site_title': 'Geändert'})
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_SETTINGS).first()
    assert log is not None
    assert log.instance_id == instance.id


# ---------------------------------------------------------------------------
# Logo Upload/Delete
# ---------------------------------------------------------------------------

def test_upload_logo_no_file_returns_400(client, admin_user, instance, temp_upload_dir):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/settings/logo', data={})
    assert rv.status_code == 400


def test_upload_logo_invalid_extension_returns_400(client, admin_user, instance, temp_upload_dir):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/settings/logo', data={
        'logo': (io.BytesIO(b'not an image'), 'logo.txt'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 400


def test_upload_logo_invalid_image_bytes_returns_400(client, admin_user, instance, temp_upload_dir):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/settings/logo', data={
        'logo': (io.BytesIO(b'garbage-not-a-real-png'), 'logo.png'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 400


def test_upload_logo_valid_image_converted_and_stored(client, admin_user, instance, temp_upload_dir):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/settings/logo', data={
        'logo': (io.BytesIO(_png_bytes('JPEG')), 'logo.jpg'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['logo_filename'] == f'logo_{instance.slug}.png'

    import os
    assert os.path.isfile(os.path.join(temp_upload_dir, data['logo_filename']))


def test_delete_logo_removes_file_and_clears_field(client, admin_user, instance, temp_upload_dir):
    c = _admin_client(client, admin_user)
    c.post(f'/api/admin/{instance.slug}/settings/logo', data={
        'logo': (io.BytesIO(_png_bytes()), 'logo.png'),
    }, content_type='multipart/form-data')

    rv = c.delete(f'/api/admin/{instance.slug}/settings/logo')
    assert rv.status_code == 200
    assert rv.get_json()['data']['logo_filename'] is None

    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    assert settings.logo_filename is None


def test_delete_logo_without_existing_logo_is_noop(client, admin_user, instance, temp_upload_dir):
    c = _admin_client(client, admin_user)
    rv = c.delete(f'/api/admin/{instance.slug}/settings/logo')
    assert rv.status_code == 200


# ---------------------------------------------------------------------------
# Global Settings
# ---------------------------------------------------------------------------

def test_get_global_settings_creates_row_if_missing(client, admin_user):
    assert _db.session.query(GlobalSettings).first() is None
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/settings/global')
    assert rv.status_code == 200
    assert _db.session.query(GlobalSettings).first() is not None


def test_update_global_settings_sanitizes_html(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.put('/api/admin/settings/global', json={
        'provider_impressum_html': '<p>Impressum</p><script>alert(1)</script>',
    })
    assert rv.status_code == 200
    assert '<script>' not in rv.get_json()['data']['provider_impressum_html']


def test_update_global_settings_validation_error(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.put('/api/admin/settings/global', json={'log_retention_months': 0})
    assert rv.status_code == 422


def test_update_global_settings_optimistic_lock_conflict(client, admin_user):
    c = _admin_client(client, admin_user)
    c.put('/api/admin/settings/global', json={'copyright_text': 'Erst'})
    stale = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rv = c.put('/api/admin/settings/global', json={'copyright_text': 'Zweitens', 'updated_at': stale})
    assert rv.status_code == 409


def test_update_global_settings_activity_log_has_no_instance(client, admin_user):
    c = _admin_client(client, admin_user)
    c.put('/api/admin/settings/global', json={'copyright_text': 'X'})
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_SETTINGS).first()
    assert log is not None
    assert log.instance_id is None


# ---------------------------------------------------------------------------
# Mail Settings
# ---------------------------------------------------------------------------

def test_get_mail_settings_creates_row_if_missing(client, admin_user):
    assert _db.session.query(MailSettings).first() is None
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/settings/mail')
    assert rv.status_code == 200
    assert _db.session.query(MailSettings).first() is not None


def test_get_mail_settings_applies_config_when_server_set(client, admin_user, app):
    ms = MailSettings(mail_server='smtp.bereits-konfiguriert.test', mail_port=465)
    _db.session.add(ms)
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/settings/mail')
    assert rv.status_code == 200
    assert app.config['MAIL_SERVER'] == 'smtp.bereits-konfiguriert.test'


def test_update_mail_settings_validation_error(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.put('/api/admin/settings/mail', json={'mail_port': 999999})
    assert rv.status_code == 422


def test_update_mail_settings_persists_and_applies_config(client, admin_user, app):
    c = _admin_client(client, admin_user)
    rv = c.put('/api/admin/settings/mail', json={
        'mail_server': 'smtp.example.test', 'mail_port': 587, 'mail_use_tls': True,
    })
    assert rv.status_code == 200
    assert app.config['MAIL_SERVER'] == 'smtp.example.test'


def test_update_mail_settings_optimistic_lock_conflict(client, admin_user):
    c = _admin_client(client, admin_user)
    c.put('/api/admin/settings/mail', json={'mail_server': 'smtp1.test'})
    stale = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rv = c.put('/api/admin/settings/mail', json={'mail_server': 'smtp2.test', 'updated_at': stale})
    assert rv.status_code == 409


# ---------------------------------------------------------------------------
# POST /settings/mail/test
# ---------------------------------------------------------------------------

@patch('app.api.admin.settings.is_mail_configured', return_value=False)
def test_send_test_mail_not_configured_returns_503(mock_configured, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test', json={})
    assert rv.status_code == 503


@patch('app.api.admin.settings.send_mail')
@patch('app.api.admin.settings.is_mail_configured', return_value=True)
def test_send_test_mail_reloads_real_mail_config_before_sending(mock_configured, mock_send, client, admin_user, app):
    """_reload_mail_config() muss bei vorhandenen DB-MailSettings die App-Config aktualisieren."""
    ms = MailSettings(mail_server='smtp.reload-test.example', mail_port=2525)
    _db.session.add(ms)
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test', json={})
    assert rv.status_code == 200
    assert app.config['MAIL_SERVER'] == 'smtp.reload-test.example'
    assert app.config['MAIL_PORT'] == 2525


@patch('app.api.admin.settings.send_mail')
@patch('app.api.admin.settings.is_mail_configured', return_value=True)
def test_send_test_mail_defaults_to_current_user_email(mock_configured, mock_send, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test', json={})
    assert rv.status_code == 200
    assert mock_send.call_args.kwargs['to'] == admin_user.email


@patch('app.api.admin.settings.send_mail')
@patch('app.api.admin.settings.is_mail_configured', return_value=True)
def test_send_test_mail_uses_explicit_recipient(mock_configured, mock_send, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test', json={'to': 'ziel@test.de'})
    assert rv.status_code == 200
    assert mock_send.call_args.kwargs['to'] == 'ziel@test.de'


@patch('app.api.admin.settings.send_mail', side_effect=RuntimeError('SMTP-Fehler'))
@patch('app.api.admin.settings.is_mail_configured', return_value=True)
def test_send_test_mail_failure_returns_500(mock_configured, mock_send, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test', json={})
    assert rv.status_code == 500


# ---------------------------------------------------------------------------
# POST /settings/mail/test-type
# ---------------------------------------------------------------------------

@patch('app.api.admin.settings.is_mail_configured', return_value=False)
def test_send_typed_test_mail_not_configured_returns_503(mock_configured, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test-type', json={'type': 'welcome', 'to': 'x@test.de'})
    assert rv.status_code == 503


@patch('app.api.admin.settings.is_mail_configured', return_value=True)
def test_send_typed_test_mail_missing_type_returns_400(mock_configured, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test-type', json={'to': 'x@test.de'})
    assert rv.status_code == 400


@patch('app.api.admin.settings.is_mail_configured', return_value=True)
def test_send_typed_test_mail_missing_recipient_returns_400(mock_configured, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test-type', json={'type': 'welcome'})
    assert rv.status_code == 400


@patch('app.api.admin.settings.send_mail')
@patch('app.api.admin.settings.is_mail_configured', return_value=True)
def test_send_typed_test_mail_unknown_type_returns_400(mock_configured, mock_send, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test-type', json={'type': 'voodoo', 'to': 'x@test.de'})
    assert rv.status_code == 400
    mock_send.assert_not_called()


@pytest.mark.parametrize('mail_type', [
    'welcome', 'organizer_invite', 'reset', 'shift_confirmation',
    'reminder', 'digest', 'dsgvo_auskunft', 'export_pdf',
])
@patch('app.api.admin.settings.send_mail')
@patch('app.api.admin.settings.is_mail_configured', return_value=True)
def test_send_typed_test_mail_all_builder_types_succeed(mock_configured, mock_send, mail_type, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test-type', json={'type': mail_type, 'to': 'x@test.de'})
    assert rv.status_code == 200
    mock_send.assert_called_once()


@patch('app.api.admin.settings.send_mail')
@patch('app.api.admin.settings.is_mail_configured', return_value=True)
def test_send_typed_test_mail_with_instance_slug_uses_instance_branding(mock_configured, mock_send, client, admin_user, instance):
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.site_title = 'Sonderinstanz'
    settings.primary_color = '#123456'
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test-type', json={
        'type': 'welcome', 'to': 'x@test.de', 'instance_slug': instance.slug,
    })
    assert rv.status_code == 200
    subject = mock_send.call_args.kwargs['subject']
    assert 'Sonderinstanz' in subject


@patch('app.api.admin.settings.send_mail', side_effect=RuntimeError('SMTP-Fehler'))
@patch('app.api.admin.settings.is_mail_configured', return_value=True)
def test_send_typed_test_mail_failure_returns_500(mock_configured, mock_send, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/settings/mail/test-type', json={'type': 'welcome', 'to': 'x@test.de'})
    assert rv.status_code == 500
