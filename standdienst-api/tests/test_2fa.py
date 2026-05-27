"""Tests für TOTP 2FA: Setup, Confirm, Verify, Disable, Backup-Codes."""
import hashlib
import pyotp
from app.extensions import db as _db
from app.models import Admin


def _create_admin(email='2faadmin@test.de'):
    admin = Admin(email=email, is_primary=True)
    admin.set_password('TestPass1!')
    _db.session.add(admin)
    _db.session.commit()
    return admin


def _login(client, email='2faadmin@test.de'):
    rv = client.post('/api/auth/login', json={'email': email, 'password': 'TestPass1!'})
    assert rv.status_code == 200
    return rv


# ---------------------------------------------------------------------------
# Setup + Confirm
# ---------------------------------------------------------------------------

def test_2fa_setup_returns_secret_and_uri(client):
    _create_admin()
    _login(client)
    rv = client.post('/api/auth/2fa/setup')
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'secret' in data
    assert 'otpauth_url' in data
    assert data['otpauth_url'].startswith('otpauth://totp/')


def test_2fa_confirm_activates_totp_and_returns_backup_codes(client):
    admin = _create_admin()
    _login(client)

    # Setup aufrufen – Secret landet in Session
    rv = client.post('/api/auth/2fa/setup')
    secret = rv.get_json()['secret']

    # Gültigen Code generieren
    code = pyotp.TOTP(secret).now()
    rv = client.post('/api/auth/2fa/confirm', json={'code': code})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'backup_codes' in data
    assert len(data['backup_codes']) == 8

    _db.session.refresh(admin)
    assert admin.totp_enabled is True
    assert admin.totp_secret == secret


def test_2fa_confirm_rejects_wrong_code(client):
    _create_admin()
    _login(client)
    client.post('/api/auth/2fa/setup')
    rv = client.post('/api/auth/2fa/confirm', json={'code': '000000'})
    assert rv.status_code == 401


def test_2fa_confirm_fails_without_setup(client):
    _create_admin()
    _login(client)
    # Kein /setup zuvor → kein Session-Secret
    rv = client.post('/api/auth/2fa/confirm', json={'code': '123456'})
    assert rv.status_code == 401


# ---------------------------------------------------------------------------
# Login mit 2FA
# ---------------------------------------------------------------------------

def test_login_requires_2fa_code_when_enabled(client):
    admin = _create_admin()
    secret = pyotp.random_base32()
    admin.totp_secret = secret
    admin.totp_enabled = True
    admin.totp_backup_codes = []
    _db.session.commit()

    rv = client.post('/api/auth/login', json={'email': admin.email, 'password': 'TestPass1!'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get('requires_2fa') is True
    # Kein JWT-Cookie gesetzt
    assert not any(k[2] == 'access_token' for k in client._cookies)


def test_2fa_verify_with_valid_totp(client):
    admin = _create_admin()
    secret = pyotp.random_base32()
    admin.totp_secret = secret
    admin.totp_enabled = True
    admin.totp_backup_codes = []
    _db.session.commit()

    client.post('/api/auth/login', json={'email': admin.email, 'password': 'TestPass1!'})
    code = pyotp.TOTP(secret).now()
    rv = client.post('/api/auth/2fa/verify', json={'code': code})
    assert rv.status_code == 200
    # client._cookies-Schlüssel sind Tupel (domain, path, name)
    assert any(k[2] == 'access_token' for k in client._cookies)


def test_2fa_verify_rejects_invalid_code(client):
    admin = _create_admin()
    secret = pyotp.random_base32()
    admin.totp_secret = secret
    admin.totp_enabled = True
    admin.totp_backup_codes = []
    _db.session.commit()

    client.post('/api/auth/login', json={'email': admin.email, 'password': 'TestPass1!'})
    rv = client.post('/api/auth/2fa/verify', json={'code': '000000'})
    assert rv.status_code == 401


def test_2fa_verify_fails_without_pending_session(client):
    _create_admin()
    rv = client.post('/api/auth/2fa/verify', json={'code': '123456'})
    assert rv.status_code == 400


# ---------------------------------------------------------------------------
# Backup-Codes
# ---------------------------------------------------------------------------

def test_backup_code_works_for_2fa_login(client):
    admin = _create_admin()
    raw_code = 'ABCD1234'
    code_hash = hashlib.sha256(raw_code.encode()).hexdigest()
    secret = pyotp.random_base32()
    admin.totp_secret = secret
    admin.totp_enabled = True
    admin.totp_backup_codes = [code_hash]
    _db.session.commit()

    client.post('/api/auth/login', json={'email': admin.email, 'password': 'TestPass1!'})
    rv = client.post('/api/auth/2fa/verify', json={'code': raw_code})
    assert rv.status_code == 200
    assert rv.get_json().get('backup_code_used') is True
    assert rv.get_json().get('remaining_backup_codes') == 0


def test_backup_code_is_consumed_after_use(client):
    admin = _create_admin()
    raw_code = 'USED1234'
    code_hash = hashlib.sha256(raw_code.encode()).hexdigest()
    secret = pyotp.random_base32()
    admin.totp_secret = secret
    admin.totp_enabled = True
    admin.totp_backup_codes = [code_hash]
    _db.session.commit()

    # Ersten Login
    client.post('/api/auth/login', json={'email': admin.email, 'password': 'TestPass1!'})
    client.post('/api/auth/2fa/verify', json={'code': raw_code})

    # Zweiten Login mit demselben Backup-Code
    client.post('/api/auth/logout')
    client.post('/api/auth/login', json={'email': admin.email, 'password': 'TestPass1!'})
    rv = client.post('/api/auth/2fa/verify', json={'code': raw_code})
    assert rv.status_code == 401, "Verbrauchter Backup-Code darf nicht erneut funktionieren"


# ---------------------------------------------------------------------------
# Disable
# ---------------------------------------------------------------------------

def test_2fa_disable_clears_totp(client):
    admin = _create_admin()
    secret = pyotp.random_base32()
    admin.totp_secret = secret
    admin.totp_enabled = True
    admin.totp_backup_codes = ['hash1']
    _db.session.commit()

    # Login mit TOTP abschließen, damit ein gültiges JWT-Cookie gesetzt wird
    client.post('/api/auth/login', json={'email': admin.email, 'password': 'TestPass1!'})
    code = pyotp.TOTP(secret).now()
    client.post('/api/auth/2fa/verify', json={'code': code})

    rv = client.post('/api/auth/2fa/disable')
    assert rv.status_code == 200

    _db.session.refresh(admin)
    assert admin.totp_enabled is False
    assert admin.totp_secret is None
    assert admin.totp_backup_codes is None
