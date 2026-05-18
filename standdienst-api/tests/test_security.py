"""Tests für Sicherheitsfeatures: JWT-Invalidierung nach Passwort-Änderung, Setup-IP-Guard."""
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from app.extensions import db as _db


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _set_reset_token(user):
    raw = secrets.token_urlsafe(32)
    user.reset_token = hashlib.sha256(raw.encode()).hexdigest()
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    _db.session.commit()
    return raw


# ---------------------------------------------------------------------------
# JWT-Invalidierung – Volunteer-Passwort-Änderung
# ---------------------------------------------------------------------------

def test_password_change_invalidates_access_token(client, instance, volunteer, volunteer_token):
    """Passwort-Änderung via PUT /profile macht das laufende Access-Token ungültig."""
    rv = client.get(f'/api/volunteer/{instance.slug}/meine-daten')
    assert rv.status_code == 200

    rv = client.put(f'/api/volunteer/{instance.slug}/profile',
                    json={'password': 'NeuesPasswort99!'})
    assert rv.status_code == 200

    # Alter Token im Cookie hat jwt_version=1, DB hat jetzt jwt_version=2
    rv = client.get(f'/api/volunteer/{instance.slug}/meine-daten')
    assert rv.status_code == 401


def test_password_change_invalidates_refresh_token(client, instance, volunteer, volunteer_token):
    """Passwort-Änderung macht auch das Refresh-Token ungültig."""
    client.put(f'/api/volunteer/{instance.slug}/profile',
               json={'password': 'NeuesPasswort99!'})

    rv = client.post('/api/auth/refresh')
    assert rv.status_code == 401


# ---------------------------------------------------------------------------
# JWT-Invalidierung – Volunteer-Passwort-Reset
# ---------------------------------------------------------------------------

def test_volunteer_reset_invalidates_existing_session(client, instance, volunteer):
    """Passwort-Reset via Token invalidiert die laufende Session."""
    client.post('/api/auth/volunteer-login', json={
        'slug': instance.slug, 'email': volunteer.email, 'password': 'TestPass1!',
    })
    rv = client.get(f'/api/volunteer/{instance.slug}/meine-daten')
    assert rv.status_code == 200

    raw = _set_reset_token(volunteer)
    rv = client.post(f'/api/public/{instance.slug}/reset-password',
                     json={'token': raw, 'password': 'NeuesPasswort99!'})
    assert rv.status_code == 200

    rv = client.get(f'/api/volunteer/{instance.slug}/meine-daten')
    assert rv.status_code == 401


# ---------------------------------------------------------------------------
# JWT-Invalidierung – Admin-Passwort-Reset
# ---------------------------------------------------------------------------

def test_admin_reset_invalidates_existing_session(client, admin_user):
    """Admin-Passwort-Reset via Token invalidiert laufende Sessions."""
    client.post('/api/auth/login',
                json={'email': admin_user.email, 'password': 'TestPass1!'})

    # Refresh-Token mit alter jwt_version=1 im Cookie
    raw = _set_reset_token(admin_user)
    rv = client.post('/api/auth/reset-password',
                     json={'token': raw, 'password': 'NeuesAdmin99!Xx', 'type': 'admin'})
    assert rv.status_code == 200

    # Refresh-Token hat noch jwt_version=1, DB jetzt jwt_version=2
    rv = client.post('/api/auth/refresh')
    assert rv.status_code == 401


# ---------------------------------------------------------------------------
# Setup-Guard – IP-Beschränkung
# ---------------------------------------------------------------------------

def test_setup_allowed_from_external_ip_without_allowlist(client, monkeypatch):
    """Ohne SETUP_ALLOWED_IPS darf jede IP das Setup aufrufen."""
    monkeypatch.delenv('SETUP_ALLOWED_IPS', raising=False)
    rv = client.post('/api/setup/admin',
                     json={'email': 'admin@test.de', 'password': 'StarkesPass1!Xx'},
                     environ_base={'REMOTE_ADDR': '1.2.3.4'})
    assert rv.status_code in (201, 409)  # IP-Block greift nicht


def test_setup_blocked_from_external_ip_with_allowlist(client, monkeypatch):
    """Mit SETUP_ALLOWED_IPS wird externe IP blockiert."""
    monkeypatch.setenv('SETUP_ALLOWED_IPS', '192.168.1.10')
    rv = client.post('/api/setup/admin',
                     json={'email': 'hacker@evil.com', 'password': 'P@ssw0rd123456'},
                     environ_base={'REMOTE_ADDR': '1.2.3.4'})
    assert rv.status_code == 403
    assert 'IP' in rv.get_json()['error']


def test_setup_config_blocked_from_external_ip_with_allowlist(client, monkeypatch):
    """POST /api/setup/config von nicht-erlaubter IP mit gesetzter Allowlist → 403."""
    monkeypatch.setenv('SETUP_ALLOWED_IPS', '192.168.1.10')
    rv = client.post('/api/setup/config',
                     json={'base_url': 'http://evil.com'},
                     environ_base={'REMOTE_ADDR': '10.0.0.1'})
    assert rv.status_code == 403


def test_setup_allowed_from_localhost(client):
    """POST /api/setup/admin von 127.0.0.1 wird inhaltlich verarbeitet (kein IP-Block)."""
    rv = client.post('/api/setup/admin',
                     json={'email': 'admin@test.de', 'password': 'StarkesPass1!Xx'},
                     environ_base={'REMOTE_ADDR': '127.0.0.1'})
    assert rv.status_code in (201, 409)


def test_setup_status_not_ip_restricted(client):
    """/api/setup/status ist öffentlich zugänglich – kein IP-Check."""
    rv = client.get('/api/setup/status', environ_base={'REMOTE_ADDR': '1.2.3.4'})
    assert rv.status_code == 200
