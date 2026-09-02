"""Funktionale Tests für app/api/passkey.py (WebAuthn).

Grundlegende Autorisierung (Besitzer-Isolation bei delete_credential, Volunteer
darf nicht mitmachen) ist bereits in test_authz_passkey.py abgedeckt.

Die reinen Optionen-Generatoren (webauthn.generate_registration_options /
generate_authentication_options) sind pure, unkritische Funktionen der
py_webauthn-Bibliothek und laufen hier real (kein Netzwerk/Kryptografie mit
externen Abhängigkeiten). Nur die Signatur-VERIFIKATION (verify_*_response),
die echte Browser-Assertions bräuchte, wird gemockt – auf
app.api.passkey.webauthn.<name>, da `import webauthn` modulweit importiert ist.
"""
import types
from unittest.mock import patch

from app.extensions import db as _db
from app.models import Admin, Organizer
from app.models.passkey import PasskeyCredential
from webauthn.helpers import bytes_to_base64url
from tests.conftest import assign_organizer as _assign, login as _login

_DUMMY_PUBLIC_KEY = bytes_to_base64url(b'dummy-public-key-bytes')


def _make_passkey(admin_id=None, organizer_id=None, credential_id='cred-1', sign_count=0):
    pk = PasskeyCredential(
        admin_id=admin_id, organizer_id=organizer_id,
        credential_id=credential_id, public_key=_DUMMY_PUBLIC_KEY, sign_count=sign_count,
    )
    _db.session.add(pk)
    _db.session.commit()
    return pk


# ---------------------------------------------------------------------------
# POST /register/begin
# ---------------------------------------------------------------------------

def test_register_begin_success_returns_options_and_sets_session(client, admin_user):
    _login(client, admin_user.email)
    rv = client.post('/api/auth/passkey/register/begin')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['rp']['name'] == 'Standdienst'
    assert 'challenge' in data
    with client.session_transaction() as sess:
        assert sess['passkey_reg_identity'] == f'admin_{admin_user.id}'


def test_register_begin_max_passkeys_returns_400(client, admin_user):
    for i in range(5):
        _make_passkey(admin_id=admin_user.id, credential_id=f'cred-{i}')
    _login(client, admin_user.email)
    rv = client.post('/api/auth/passkey/register/begin')
    assert rv.status_code == 400


# ---------------------------------------------------------------------------
# POST /register/complete
# ---------------------------------------------------------------------------

def test_register_complete_without_pending_registration_returns_400(client, admin_user):
    _login(client, admin_user.email)
    rv = client.post('/api/auth/passkey/register/complete', json={'name': 'Mein Handy'})
    assert rv.status_code == 400


@patch('app.api.passkey.webauthn.verify_registration_response', side_effect=Exception('Signatur ungültig'))
def test_register_complete_verification_failure_returns_400(mock_verify, client, admin_user):
    _login(client, admin_user.email)
    client.post('/api/auth/passkey/register/begin')
    rv = client.post('/api/auth/passkey/register/complete', json={'name': 'Mein Handy'})
    assert rv.status_code == 400


@patch('app.api.passkey.webauthn.verify_registration_response')
def test_register_complete_success_creates_credential(mock_verify, client, admin_user):
    mock_verify.return_value = types.SimpleNamespace(
        credential_id=b'neue-credential-id', credential_public_key=b'neuer-public-key', sign_count=0,
    )
    _login(client, admin_user.email)
    client.post('/api/auth/passkey/register/begin')
    rv = client.post('/api/auth/passkey/register/complete', json={'name': 'Mein Handy'})
    assert rv.status_code == 201
    data = rv.get_json()
    assert data['credential']['name'] == 'Mein Handy'

    pk = _db.session.query(PasskeyCredential).filter_by(admin_id=admin_user.id).first()
    assert pk is not None
    assert pk.name == 'Mein Handy'


@patch('app.api.passkey.webauthn.verify_registration_response')
def test_register_complete_for_organizer_sets_organizer_id(mock_verify, client, instance, organizer_user):
    mock_verify.return_value = types.SimpleNamespace(
        credential_id=b'org-cred-id', credential_public_key=b'org-public-key', sign_count=0,
    )
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    client.post('/api/auth/passkey/register/begin')
    rv = client.post('/api/auth/passkey/register/complete', json={})
    assert rv.status_code == 201

    pk = _db.session.query(PasskeyCredential).filter_by(organizer_id=organizer_user.id).first()
    assert pk is not None
    assert pk.admin_id is None


# ---------------------------------------------------------------------------
# POST /authenticate/begin
# ---------------------------------------------------------------------------

def test_authenticate_begin_returns_options_and_sets_session_challenge(client):
    rv = client.post('/api/auth/passkey/authenticate/begin')
    assert rv.status_code == 200
    assert 'challenge' in rv.get_json()
    with client.session_transaction() as sess:
        assert sess.get('passkey_auth_challenge') is not None


# ---------------------------------------------------------------------------
# POST /authenticate/complete
# ---------------------------------------------------------------------------

def test_authenticate_complete_without_challenge_returns_400(client):
    rv = client.post('/api/auth/passkey/authenticate/complete', json={'id': 'irgendeine-id'})
    assert rv.status_code == 400


def test_authenticate_complete_unknown_credential_returns_401(client):
    client.post('/api/auth/passkey/authenticate/begin')
    rv = client.post('/api/auth/passkey/authenticate/complete', json={'id': 'unbekannte-id'})
    assert rv.status_code == 401


@patch('app.api.passkey.webauthn.verify_authentication_response', side_effect=Exception('Signatur ungültig'))
def test_authenticate_complete_verification_failure_returns_401(mock_verify, client, admin_user):
    _make_passkey(admin_id=admin_user.id, credential_id='cred-x')
    client.post('/api/auth/passkey/authenticate/begin')
    rv = client.post('/api/auth/passkey/authenticate/complete', json={'id': 'cred-x'})
    assert rv.status_code == 401


@patch('app.api.passkey.webauthn.verify_authentication_response')
def test_authenticate_complete_success_logs_in_admin_and_updates_sign_count(mock_verify, client, admin_user):
    pk = _make_passkey(admin_id=admin_user.id, credential_id='cred-admin', sign_count=3)
    mock_verify.return_value = types.SimpleNamespace(new_sign_count=4)

    client.post('/api/auth/passkey/authenticate/begin')
    rv = client.post('/api/auth/passkey/authenticate/complete', json={'id': 'cred-admin'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['user']['role'] == 'admin'
    assert data['user']['email'] == admin_user.email
    assert 'access_token' in rv.headers.get('Set-Cookie', '')

    _db.session.refresh(pk)
    assert pk.sign_count == 4
    assert pk.last_used_at is not None


@patch('app.api.passkey.webauthn.verify_authentication_response')
def test_authenticate_complete_success_logs_in_organizer(mock_verify, client, instance, organizer_user):
    _assign(organizer_user, instance)
    _make_passkey(organizer_id=organizer_user.id, credential_id='cred-org')
    mock_verify.return_value = types.SimpleNamespace(new_sign_count=1)

    client.post('/api/auth/passkey/authenticate/begin')
    rv = client.post('/api/auth/passkey/authenticate/complete', json={'id': 'cred-org'})
    assert rv.status_code == 200
    assert rv.get_json()['user']['role'] == 'organizer'


# ---------------------------------------------------------------------------
# DELETE /credentials/<id>
# ---------------------------------------------------------------------------

def test_delete_credential_not_found_returns_404(client, admin_user):
    _login(client, admin_user.email)
    rv = client.delete('/api/auth/passkey/credentials/99999')
    assert rv.status_code == 404


def test_register_begin_user_deleted_after_login_returns_404(client, admin_user):
    """JWT bleibt gültig, obwohl der Account inzwischen gelöscht wurde -> _load_user() liefert None."""
    _login(client, admin_user.email)
    _db.session.delete(admin_user)
    _db.session.commit()
    rv = client.post('/api/auth/passkey/register/begin')
    assert rv.status_code == 404


# ---------------------------------------------------------------------------
# _rp_config – sicherheitsrelevante Origin-Ableitung
# ---------------------------------------------------------------------------

def test_rp_config_explicit_origin_override(app):
    from app.api.passkey import _rp_config
    old = app.config.get('WEBAUTHN_ORIGIN')
    app.config['WEBAUTHN_ORIGIN'] = 'https://passkeys.example.test/'
    try:
        rp_id, origin = _rp_config()
    finally:
        app.config['WEBAUTHN_ORIGIN'] = old
    assert rp_id == 'passkeys.example.test'
    assert origin == 'https://passkeys.example.test'


def test_rp_config_derives_from_frontend_url_strips_default_port(app):
    from app.api.passkey import _rp_config
    old_origin = app.config.get('WEBAUTHN_ORIGIN')
    old_frontend = app.config.get('FRONTEND_URL')
    app.config['WEBAUTHN_ORIGIN'] = ''
    app.config['FRONTEND_URL'] = 'https://standdienst.example.test:443'
    try:
        rp_id, origin = _rp_config()
    finally:
        app.config['WEBAUTHN_ORIGIN'] = old_origin
        app.config['FRONTEND_URL'] = old_frontend
    assert rp_id == 'standdienst.example.test'
    assert origin == 'https://standdienst.example.test'  # :443 entfernt
