"""Alle ausgehenden Mails müssen Links auf die im Setup konfigurierte Basis-URL
(GlobalSettings.base_url) enthalten – nicht auf FRONTEND_URL, deren Default
http://localhost:5173 ist.

Regression: In Produktion enthielten Mails localhost-Links, weil einige Stellen
FRONTEND_URL direkt lasen statt _base_url() (GlobalSettings → FRONTEND_URL).
"""
from datetime import date, time, datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.extensions import db as _db
from app.models import (
    GlobalSettings, Stand, EventDate, Shift, Registration,
)
from app.utils.scheduler import _send_reminders, _send_organizer_digest
from tests.conftest import login as _login, assign_organizer

BASE = 'https://standdienst.example.org'


@pytest.fixture
def base_url_configured(app):
    gs = GlobalSettings.query.first()
    if not gs:
        gs = GlobalSettings()
        _db.session.add(gs)
    gs.base_url = BASE
    _db.session.commit()
    return BASE


def _html(mock_send):
    mock_send.assert_called_once()
    call = mock_send.call_args
    return call.kwargs.get('html') or call.args[2]


def _assert_links_use_base_url(html):
    assert 'localhost' not in html
    assert f'href="{BASE}/' in html


def _make_shift(instance, day):
    stand = Stand(instance_id=instance.id, name='Kasse', sort_order=0)
    _db.session.add(stand)
    _db.session.flush()
    ed = EventDate(instance_id=instance.id, date=day, is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    shift = Shift(stand_id=stand.id, event_date_id=ed.id,
                  start_time=time(10, 0), end_time=time(12, 0), max_volunteers=5)
    _db.session.add(shift)
    _db.session.commit()
    return shift


@patch('app.api.volunteer.send_mail')
@patch('app.api.volunteer.is_mail_configured', return_value=True)
def test_shift_confirmation_uses_base_url(mock_configured, mock_send, client, instance, volunteer,
                                         volunteer_token, base_url_configured):
    shift = _make_shift(instance, date(2026, 9, 1))
    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 201
    html = _html(mock_send)
    _assert_links_use_base_url(html)
    assert f'{BASE}/{instance.slug}/my-shifts' in html


@patch('app.api.volunteer.send_mail')
@patch('app.api.volunteer.is_mail_configured', return_value=True)
def test_volunteer_daten_auskunft_uses_base_url(mock_configured, mock_send, client, instance, volunteer,
                                                volunteer_token, base_url_configured):
    rv = client.post(f'/api/volunteer/{instance.slug}/meine-daten/export')
    assert rv.status_code == 200
    _assert_links_use_base_url(_html(mock_send))


@patch('app.api.admin.volunteers.send_mail')
@patch('app.api.admin.volunteers.is_mail_configured', return_value=True)
def test_admin_dsgvo_auskunft_uses_base_url(mock_configured, mock_send, client, admin_user, instance, volunteer,
                                            base_url_configured):
    _login(client, admin_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}/dsgvo-auskunft')
    assert rv.status_code == 200
    _assert_links_use_base_url(_html(mock_send))


@patch('app.api.admin.volunteers.send_mail')
@patch('app.api.admin.volunteers.is_mail_configured', return_value=True)
def test_admin_created_volunteer_welcome_falls_back_to_frontend_url(mock_configured, mock_send, app, client,
                                                                   admin_user, instance):
    """Ohne Setup-Basis-URL greift FRONTEND_URL – keine relativen Links."""
    _login(client, admin_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/volunteers', json={
        'first_name': 'Eingeladen', 'email': 'eingeladen@test.de',
    })
    assert rv.status_code == 201
    frontend = app.config['FRONTEND_URL'].rstrip('/')
    assert f'{frontend}/{instance.slug}/welcome/' in _html(mock_send)


@patch('app.api.auth.send_mail')
def test_admin_forgot_password_uses_base_url(mock_send, client, admin_user, base_url_configured):
    rv = client.post('/api/auth/forgot-password', json={'email': admin_user.email, 'type': 'admin'})
    assert rv.status_code == 200
    html = _html(mock_send)
    _assert_links_use_base_url(html)
    assert f'{BASE}/admin/reset-password?token=' in html


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_reminder_uses_base_url(mock_configured, mock_send, app, instance, volunteer, base_url_configured):
    volunteer.notifications_enabled = True
    shift = _make_shift(instance, date.today() + timedelta(days=1))
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    _send_reminders(app)

    _assert_links_use_base_url(_html(mock_send))


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_organizer_digest_uses_base_url(mock_configured, mock_send, app, instance, organizer_user, volunteer,
                                        base_url_configured):
    assign_organizer(organizer_user, instance)
    shift = _make_shift(instance, date.today() - timedelta(days=1))
    reg = Registration(volunteer_id=volunteer.id, shift_id=shift.id)
    _db.session.add(reg)
    _db.session.commit()
    reg.registered_at = datetime.now(timezone.utc) - timedelta(days=1)
    _db.session.commit()

    _send_organizer_digest(app)

    html = _html(mock_send)
    _assert_links_use_base_url(html)
    assert f'{BASE}/admin/profile' in html


@pytest.mark.parametrize('kind', ['dienste', 'essen'])
@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_export_mail_uses_base_url(mock_configured, mock_send, kind, client, admin_user, instance,
                                   base_url_configured):
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add(ed)
    _db.session.commit()
    _login(client, admin_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/export/pdf/{kind}',
                     json={'date_ids': [ed.id], 'email': 'empfaenger@test.de'})
    assert rv.status_code == 200
    _assert_links_use_base_url(_html(mock_send))


@patch('app.api.auth.send_mail')
def test_admin_forgot_password_without_base_url_still_200(mock_send, monkeypatch, app, client, admin_user):
    """Fehlende Basis-URL darf keinen 500er erzeugen (sonst Account-Enumeration)."""
    monkeypatch.setitem(app.config, 'FRONTEND_URL', '')
    rv = client.post('/api/auth/forgot-password', json={'email': admin_user.email, 'type': 'admin'})
    assert rv.status_code == 200
    mock_send.assert_not_called()
