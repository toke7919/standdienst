"""Tests für den neuen passwortlosen Registrierungsflow."""
import base64
import hashlib
import json
from app.extensions import db as _db
from app.models import Volunteer, SiteSettings, GlobalSettings


def _altcha_solution(client, slug) -> str:
    """Löst die Altcha-Challenge für Tests (ALTCHA_MAX_NUMBER=100 in TestingConfig)."""
    rv = client.get(f'/api/public/{slug}/captcha')
    ch = rv.get_json()
    for n in range(ch['maxnumber'] + 1):
        if hashlib.sha256(f"{ch['salt']}{n}".encode()).hexdigest() == ch['challenge']:
            payload = {
                'algorithm': ch['algorithm'],
                'challenge': ch['challenge'],
                'number': n,
                'salt': ch['salt'],
                'signature': ch['signature'],
            }
            return base64.b64encode(json.dumps(payload).encode()).decode()
    raise AssertionError('Altcha: keine Lösung gefunden')


# ---------------------------------------------------------------------------
# Anonyme Registrierung (keine E-Mail) → Direktlogin
# ---------------------------------------------------------------------------

def test_register_anonymous_direct_login(client, instance):
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Anonym',
        'last_name': 'Tester',
        'altcha': answer,
    })
    assert rv.status_code == 201
    data = rv.get_json()
    assert 'user' in data
    assert data['user']['role'] == 'volunteer'
    assert data['user']['email'] is None


def test_register_anonymous_no_password_set(client, instance):
    answer = _altcha_solution(client, instance.slug)
    client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Kein',
        'last_name': 'PW',
        'altcha': answer,
    })
    v = Volunteer.query.filter_by(instance_id=instance.id, name='Kein PW').first()
    assert v is not None
    assert v.password_hash is None


# ---------------------------------------------------------------------------
# E-Mail-Registrierung → Welcome-Token-Flow
# ---------------------------------------------------------------------------

def test_register_with_email_direct_login(client, instance):
    """E-Mail-Registrierung → Nutzer wird direkt eingeloggt + Welcome-Mail-Hinweis."""
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Mail',
        'last_name': 'Tester',
        'email': 'mailtester@test.de',
        'altcha': answer,
    })
    assert rv.status_code == 201
    data = rv.get_json()
    assert 'user' in data
    assert data['user']['email'] == 'mailtester@test.de'
    assert 'E-Mail' in data['message']


def test_register_email_creates_welcome_token(client, instance):
    answer = _altcha_solution(client, instance.slug)
    client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Token',
        'last_name': 'Tester',
        'email': 'tokentest@test.de',
        'altcha': answer,
    })
    v = Volunteer.query.filter_by(instance_id=instance.id, email='tokentest@test.de').first()
    assert v is not None
    assert v.welcome_token is not None
    assert v.welcome_token_expires is not None
    assert v.password_hash is None


def test_welcome_setup_sets_password_and_logs_in(client, instance):
    answer = _altcha_solution(client, instance.slug)
    client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Setup',
        'last_name': 'Tester',
        'email': 'setup@test.de',
        'altcha': answer,
    })
    v = Volunteer.query.filter_by(email='setup@test.de').first()

    # Rohtoken rekonstruieren geht nicht; raw_token simulieren via Token direkt
    import secrets
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    v.welcome_token = token_hash
    _db.session.commit()

    # GET – Info abrufen
    rv = client.get(f'/api/public/{instance.slug}/welcome/{raw}')
    assert rv.status_code == 200
    assert rv.get_json()['data']['name'] == 'Setup Tester'

    # POST – Passwort setzen
    rv = client.post(f'/api/public/{instance.slug}/welcome/{raw}',
                     json={'password': 'NeuesPasswort1!'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'user' in data
    assert data['user']['email'] == 'setup@test.de'

    # Token verbraucht
    _db.session.refresh(v)
    assert v.welcome_token is None
    assert v.password_hash is not None


def test_welcome_setup_weak_password_rejected(client, instance):
    answer = _altcha_solution(client, instance.slug)
    client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Weak',
        'last_name': 'PW',
        'email': 'weak@test.de',
        'altcha': answer,
    })
    v = Volunteer.query.filter_by(email='weak@test.de').first()
    import secrets
    raw = secrets.token_urlsafe(32)
    v.welcome_token = hashlib.sha256(raw.encode()).hexdigest()
    _db.session.commit()

    rv = client.post(f'/api/public/{instance.slug}/welcome/{raw}',
                     json={'password': 'kurz'})
    assert rv.status_code == 400


def test_welcome_invalid_token(client, instance):
    rv = client.get(f'/api/public/{instance.slug}/welcome/ungueltig123')
    assert rv.status_code == 400


# ---------------------------------------------------------------------------
# Datenschutzerklärung – Consent nur erzwungen wenn Policy konfiguriert
# ---------------------------------------------------------------------------

def test_register_consent_not_required_without_policy(client, instance):
    """Keine Datenschutzerklärung konfiguriert → consent optional."""
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Kein',
        'last_name': 'Consent',
        'altcha': answer,
        'consent': False,
    })
    assert rv.status_code == 201


def test_register_consent_required_with_policy(client, instance):
    """Datenschutzerklärung konfiguriert → consent Pflicht."""
    gs = GlobalSettings()
    gs.datenschutz_template_html = '<p>Datenschutz</p>'
    _db.session.add(gs)
    _db.session.commit()

    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Kein',
        'last_name': 'Consent',
        'altcha': answer,
        'consent': False,
    })
    assert rv.status_code == 400
    assert 'Datenschutz' in rv.get_json()['error']


def test_register_consent_accepted_with_policy(client, instance):
    gs = GlobalSettings()
    gs.datenschutz_template_html = '<p>Datenschutz</p>'
    _db.session.add(gs)
    _db.session.commit()

    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Mit',
        'last_name': 'Consent',
        'altcha': answer,
        'consent': True,
    })
    assert rv.status_code == 201
    v = Volunteer.query.filter_by(instance_id=instance.id, name='Mit Consent').first()
    assert v.consent_given_at is not None


# ---------------------------------------------------------------------------
# Datenschutz-Endpunkt
# ---------------------------------------------------------------------------

def test_datenschutz_endpoint(client, instance):
    rv = client.get(f'/api/public/{instance.slug}/datenschutz')
    assert rv.status_code == 200
    assert 'privacy_policy_html' in rv.get_json()['data']
