"""Funktionale Tests für app/api/setup.py.

Der Blueprint ist nur solange GlobalSettings.setup_complete=False erreichbar
(außer /status). Keine Auth-Decorators – die Absicherung läuft über
_check_guard() (403 nach Abschluss) und optional _check_setup_ip()
(SETUP_ALLOWED_IPS-Env-Var, per Default keine Einschränkung).
"""
import os
from unittest.mock import patch

import pytest

from app.extensions import db as _db
from app.models import Admin, GlobalSettings, MailSettings
from app.utils.settings_cache import _cache


def _make_admin():
    a = Admin(email='bereits@test.de', is_primary=True)
    a.set_password('BereitsPass1!')
    _db.session.add(a)
    _db.session.commit()
    return a


def _complete_setup():
    gs = GlobalSettings(setup_complete=True)
    _db.session.add(gs)
    _db.session.commit()
    _cache.clear()
    return gs


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------

def test_status_fresh_install(client):
    # _seed_admin() (app/__init__.py) legt beim allerersten App-Start testweise
    # anhand von ADMIN_PASSWORD einen Admin an und markiert Setup als
    # abgeschlossen, damit andere Tests nicht durch den Setup-Guard blockiert
    # werden. Für diesen Test daher explizit den unkonfigurierten Zustand
    # herstellen, statt auf Ausführungsreihenfolge zu vertrauen.
    _db.session.query(Admin).delete()
    _db.session.query(GlobalSettings).delete()
    _db.session.commit()
    _cache.clear()

    rv = client.get('/api/setup/status')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data == {'setup_complete': False, 'has_admin': False, 'maintenance_mode': False}


def test_status_reflects_admin_and_completion(client):
    _make_admin()
    gs = _complete_setup()
    gs.maintenance_mode = True
    _db.session.commit()
    _cache.clear()

    rv = client.get('/api/setup/status')
    data = rv.get_json()['data']
    assert data == {'setup_complete': True, 'has_admin': True, 'maintenance_mode': True}


# ---------------------------------------------------------------------------
# POST /admin
# ---------------------------------------------------------------------------

def test_create_admin_missing_fields_returns_400(client):
    rv = client.post('/api/setup/admin', json={'email': 'x@test.de'})
    assert rv.status_code == 400


def test_create_admin_weak_password_returns_400(client):
    """Setup-Admin ist ein Admin-Account -> 12-Zeichen-Komplexitätsregel gilt."""
    rv = client.post('/api/setup/admin', json={'email': 'x@test.de', 'password': 'schwachaberlang'})
    assert rv.status_code == 400


def test_create_admin_success(client):
    rv = client.post('/api/setup/admin', json={'email': 'erst@test.de', 'password': 'SicheresPass1!'})
    assert rv.status_code == 201
    admin = _db.session.query(Admin).filter_by(email='erst@test.de').first()
    assert admin is not None
    assert admin.is_primary is True


def test_create_admin_second_time_returns_409(client):
    _make_admin()
    rv = client.post('/api/setup/admin', json={'email': 'zweiter@test.de', 'password': 'SicheresPass1!'})
    assert rv.status_code == 409


def test_create_admin_blocked_after_setup_complete(client):
    _complete_setup()
    rv = client.post('/api/setup/admin', json={'email': 'x@test.de', 'password': 'SicheresPass1!'})
    assert rv.status_code == 403


def test_create_admin_blocked_for_disallowed_ip(client):
    with patch.dict(os.environ, {'SETUP_ALLOWED_IPS': '10.0.0.1'}):
        rv = client.post('/api/setup/admin', json={'email': 'x@test.de', 'password': 'SicheresPass1!'},
                         environ_overrides={'REMOTE_ADDR': '203.0.113.5'})
    assert rv.status_code == 403


def test_create_admin_allowed_for_localhost_even_with_ip_restriction(client):
    with patch.dict(os.environ, {'SETUP_ALLOWED_IPS': '10.0.0.1'}):
        rv = client.post('/api/setup/admin', json={'email': 'x@test.de', 'password': 'SicheresPass1!'},
                         environ_overrides={'REMOTE_ADDR': '127.0.0.1'})
    assert rv.status_code == 201


# ---------------------------------------------------------------------------
# POST /config
# ---------------------------------------------------------------------------

def test_save_config_creates_global_settings(client):
    assert _db.session.query(GlobalSettings).first() is None
    rv = client.post('/api/setup/config', json={
        'base_url': 'https://standdienst.example.test/', 'github_pat': 'ghp_x', 'timezone': 'Europe/Vienna',
    })
    assert rv.status_code == 200
    gs = _db.session.query(GlobalSettings).first()
    assert gs.base_url == 'https://standdienst.example.test'  # trailing slash entfernt
    assert gs.github_pat == 'ghp_x'
    assert gs.timezone == 'Europe/Vienna'


def test_save_config_empty_base_url_becomes_none(client):
    rv = client.post('/api/setup/config', json={'base_url': ''})
    assert rv.status_code == 200
    gs = _db.session.query(GlobalSettings).first()
    assert gs.base_url is None


def test_save_config_blocked_after_setup_complete(client):
    _complete_setup()
    rv = client.post('/api/setup/config', json={'base_url': 'https://x.test'})
    assert rv.status_code == 403


# ---------------------------------------------------------------------------
# POST /mail
# ---------------------------------------------------------------------------

def test_save_mail_creates_mail_settings_with_defaults(client):
    assert _db.session.query(MailSettings).first() is None
    rv = client.post('/api/setup/mail', json={'server': 'smtp.example.test'})
    assert rv.status_code == 200
    ms = _db.session.query(MailSettings).first()
    assert ms.mail_server == 'smtp.example.test'
    assert ms.mail_port == 587
    assert ms.mail_use_tls is True


def test_save_mail_custom_values(client):
    rv = client.post('/api/setup/mail', json={
        'server': 'smtp.example.test', 'port': 465, 'use_tls': False,
        'username': 'user', 'password': 'pw', 'sender': 'noreply@test.de', 'sender_name': 'Standdienst',
    })
    assert rv.status_code == 200
    ms = _db.session.query(MailSettings).first()
    assert ms.mail_port == 465
    assert ms.mail_use_tls is False
    assert ms.mail_default_sender == 'noreply@test.de'


def test_save_mail_blocked_after_setup_complete(client):
    _complete_setup()
    rv = client.post('/api/setup/mail', json={'server': 'smtp.example.test'})
    assert rv.status_code == 403


# ---------------------------------------------------------------------------
# POST /finish
# ---------------------------------------------------------------------------

def test_finish_without_admin_returns_400(client):
    rv = client.post('/api/setup/finish')
    assert rv.status_code == 400


def test_finish_success_sets_setup_complete(client):
    _make_admin()
    rv = client.post('/api/setup/finish')
    assert rv.status_code == 200
    gs = _db.session.query(GlobalSettings).first()
    assert gs.setup_complete is True


def test_finish_twice_returns_403(client):
    _make_admin()
    client.post('/api/setup/finish')
    rv = client.post('/api/setup/finish')
    assert rv.status_code == 403


def test_finish_invalidates_settings_cache(client):
    _make_admin()
    from app.utils.settings_cache import get_global_settings
    get_global_settings()  # füllt den Cache mit setup_complete=False
    assert _cache.get('g') is not None

    client.post('/api/setup/finish')
    # Cache muss invalidiert sein -> nächster Read holt den frischen (True) Wert
    gs = get_global_settings()
    assert gs.setup_complete is True
