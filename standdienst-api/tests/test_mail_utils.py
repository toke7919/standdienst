"""Unit-Tests für app/utils/mail.py – reine Utility-Funktionen (kein Blueprint).

Die meisten HTML-Mail-Builder (build_welcome_email, build_organizer_invite_email,
build_reminder_email, ...) laufen bereits über die parametrisierten Testmail-Tests
in test_settings.py real (nicht gemockt) durch und sind dadurch schon weitgehend
abgedeckt. Hier fokussiert auf das, was sonst nirgends real durchlaufen wird:
send_mail()'s Retry-/Backoff-Logik, is_mail_configured()'s DB-Fallback, die
Logo-Hilfsfunktionen, _html_to_text() und build_invite_email/
build_registration_email (letztere sind ohne eigenen Aufrufer in der API,
build_invite_email wird von admins.py genutzt).
"""
import os
import tempfile
from unittest.mock import patch

import pytest

from app.extensions import db as _db
from app.models import MailSettings
from app.utils.mail import (
    is_mail_configured, send_mail, get_logo_for_email, get_platform_logo_for_email,
    _html_to_text, build_invite_email, build_registration_email, build_reminder_email,
)


@pytest.fixture
def no_configured_mail_server(app):
    """TestingConfig setzt MAIL_SERVER='localhost' -> für den DB-Fallback-Test
    muss das temporär zurückgesetzt werden."""
    old = app.config.get('MAIL_SERVER')
    app.config['MAIL_SERVER'] = ''
    yield
    app.config['MAIL_SERVER'] = old


# ---------------------------------------------------------------------------
# is_mail_configured
# ---------------------------------------------------------------------------

def test_is_mail_configured_true_via_app_config(app):
    assert is_mail_configured(app) is True


def test_is_mail_configured_false_without_server_or_db_row(no_configured_mail_server):
    assert is_mail_configured() is False


def test_is_mail_configured_true_via_db_fallback(no_configured_mail_server):
    _db.session.add(MailSettings(mail_server='smtp.db.test'))
    _db.session.commit()
    assert is_mail_configured() is True


# ---------------------------------------------------------------------------
# send_mail – Retry/Backoff
# ---------------------------------------------------------------------------

@patch('app.utils.mail.mail.send')
def test_send_mail_success_first_try(mock_send):
    send_mail('empfaenger@test.de', 'Betreff', '<p>Hallo</p>')
    mock_send.assert_called_once()


@patch('app.utils.mail.mail.send', side_effect=[Exception('SMTP kaputt'), None])
def test_send_mail_retries_after_failure_then_succeeds(mock_send):
    send_mail('empfaenger@test.de', 'Betreff', '<p>Hallo</p>', retries=3)
    assert mock_send.call_count == 2


@patch('app.utils.mail.mail.send', side_effect=RuntimeError('SMTP dauerhaft kaputt'))
def test_send_mail_raises_last_exception_after_exhausting_retries(mock_send):
    with pytest.raises(RuntimeError, match='SMTP dauerhaft kaputt'):
        send_mail('empfaenger@test.de', 'Betreff', '<p>Hallo</p>', retries=2)
    assert mock_send.call_count == 2


@patch('app.utils.mail.mail.send')
def test_send_mail_attaches_files(mock_send):
    send_mail('empfaenger@test.de', 'Betreff', '<p>Hallo</p>',
              attachments=[('anhang.pdf', 'application/pdf', b'%PDF-fake')])
    msg = mock_send.call_args.args[0]
    assert len(msg.attachments) == 1
    assert msg.attachments[0].filename == 'anhang.pdf'


@patch('app.utils.mail.mail.send')
def test_send_mail_sender_name_strips_crlf(mock_send):
    """CRLF im Absendernamen könnte sonst SMTP-Header-Injection ermöglichen."""
    send_mail('empfaenger@test.de', 'Betreff', '<p>Hallo</p>',
              sender_name='Böse\r\nBcc: angreifer@evil.test')
    msg = mock_send.call_args.args[0]
    assert '\r' not in msg.sender
    assert '\n' not in msg.sender


@patch('app.utils.mail.mail.send')
def test_send_mail_uses_plain_text_fallback_from_html(mock_send):
    send_mail('empfaenger@test.de', 'Betreff', '<p>Hallo <strong>Welt</strong></p>')
    msg = mock_send.call_args.args[0]
    assert 'Hallo' in msg.body
    assert '<p>' not in msg.body


# ---------------------------------------------------------------------------
# get_logo_for_email / get_platform_logo_for_email
# ---------------------------------------------------------------------------

def test_get_logo_for_email_none_when_no_filename():
    assert get_logo_for_email(None, 'https://x.test') is None


def test_get_logo_for_email_returns_base64_when_file_exists(app):
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, 'logo.png'), 'wb') as f:
            f.write(b'\x89PNG-fake-bytes')
        old = app.config.get('UPLOAD_FOLDER')
        app.config['UPLOAD_FOLDER'] = tmp
        try:
            result = get_logo_for_email('logo.png', 'https://x.test')
        finally:
            app.config['UPLOAD_FOLDER'] = old
    assert result.startswith('data:image/png;base64,')


def test_get_logo_for_email_falls_back_to_url_when_file_missing(app):
    old = app.config.get('UPLOAD_FOLDER')
    app.config['UPLOAD_FOLDER'] = '/nonexistent-dir-fuer-test-xyz'
    try:
        result = get_logo_for_email('logo.png', 'https://x.test')
    finally:
        app.config['UPLOAD_FOLDER'] = old
    assert result == 'https://x.test/uploads/logo.png'


def test_get_platform_logo_for_email_none_when_not_found(app):
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(app, 'root_path', tmp):
            assert get_platform_logo_for_email() is None


# ---------------------------------------------------------------------------
# _html_to_text
# ---------------------------------------------------------------------------

def test_html_to_text_converts_paragraphs_and_br():
    text = _html_to_text('<p>Zeile1</p><p>Zeile2<br>Zeile3</p>')
    assert 'Zeile1' in text
    assert 'Zeile2' in text
    assert 'Zeile3' in text


def test_html_to_text_converts_links_to_text_with_url():
    text = _html_to_text('<a href="https://example.test">Klick hier</a>')
    assert 'Klick hier (https://example.test)' in text


def test_html_to_text_strips_remaining_tags():
    text = _html_to_text('<div><span>Text</span></div>')
    assert '<' not in text
    assert 'Text' in text


# ---------------------------------------------------------------------------
# build_invite_email / build_registration_email
# ---------------------------------------------------------------------------

def test_build_invite_email_contains_name_role_and_login_url():
    html = build_invite_email('Max Mustermann', 'Administrator', 'https://x.test/admin/login', 'https://x.test')
    assert 'Max Mustermann' in html
    assert 'Administrator' in html
    assert 'https://x.test/admin/login' in html


def test_build_registration_email_contains_name_and_login_url():
    html = build_registration_email('Max Mustermann', 'Testinstanz', 'https://x.test/login')
    assert 'Max Mustermann' in html
    assert 'Testinstanz' in html
    assert 'https://x.test/login' in html


def test_build_reminder_email_lists_food_items_with_delivery_details():
    """In test_settings.py wird der Testmail-Typ 'reminder' immer mit food_items=[]
    aufgerufen -> die Essensspenden-Sektion wird dort nie real durchlaufen."""
    html = build_reminder_email(
        'Max Mustermann',
        shifts=[],
        food_items=[{
            'name': 'Kuchen', 'description': 'Apfelkuchen',
            'delivery_time': '10:00', 'delivery_location': 'Küche',
        }],
        instance_title='Testinstanz',
        base_url='https://x.test',
    )
    assert 'Essensspenden morgen' in html
    assert 'Apfelkuchen' in html
    assert '10:00' in html
    assert 'Küche' in html
