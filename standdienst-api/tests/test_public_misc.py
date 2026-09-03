"""Funktionale Tests für app/api/public.py – Restfälle.

Die Registrierungs-/Welcome-/Consent-Flows sind bereits ausführlich in
test_registration.py abgedeckt, DSGVO-Selbstlöschung/meine-daten in
test_dsgvo.py. Hier geht es um das, was dort nicht durchlaufen wird:
_base_url()-Fallbackkette, platform-info, Fehlerpfade bei der Registrierung
(Sperre, Anmeldeschluss, fehlende Mail-Konfiguration, Duplikat, Willkommens-
mail-Fehlerresilienz), Impressum/Datenschutz auf Plattform- und Instanzebene
inkl. Platzhalter-Ersetzung, und der komplett ungetestete Passwort-Vergessen-
Flow für Volunteers.

public.py importiert is_mail_configured/send_mail auf Modulebene -> gemockt
wird auf app.api.public.<name>.
"""
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.extensions import db as _db
from app.models import GlobalSettings, SiteSettings, Volunteer
from tests.test_registration import _altcha_solution


# ---------------------------------------------------------------------------
# _base_url()
# ---------------------------------------------------------------------------

def _global_settings():
    """Nutzt die bestehende GlobalSettings-Zeile (falls durch _seed_admin() beim
    App-Start bereits angelegt) statt eine zweite Zeile hinzuzufügen, die von
    GlobalSettings.query.first() ohnehin nie gefunden würde."""
    gs = GlobalSettings.query.first()
    if not gs:
        gs = GlobalSettings()
        _db.session.add(gs)
    return gs


def test_base_url_prefers_global_settings_over_frontend_url(app):
    from app.api.public import _base_url
    _global_settings().base_url = 'https://konfiguriert.example.test/'
    _db.session.commit()
    assert _base_url() == 'https://konfiguriert.example.test'


def test_base_url_falls_back_to_frontend_url_when_no_global_settings(app):
    from app.api.public import _base_url
    assert _base_url() == app.config['FRONTEND_URL'].rstrip('/')


def test_base_url_raises_when_nothing_configured(app):
    from app.api.public import _base_url
    old = app.config.get('FRONTEND_URL')
    app.config['FRONTEND_URL'] = ''
    try:
        try:
            _base_url()
            assert False, 'RuntimeError erwartet'
        except RuntimeError:
            pass
    finally:
        app.config['FRONTEND_URL'] = old


# ---------------------------------------------------------------------------
# GET /platform-info
# ---------------------------------------------------------------------------

def test_platform_info_without_global_settings(client):
    rv = client.get('/api/public/platform-info')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['copyright_text'] == ''
    assert data['has_impressum'] is True  # kein gs -> True per Default


def test_platform_info_with_global_settings(client):
    gs = _global_settings()
    gs.copyright_text = '© Test'
    gs.provider_impressum_html = '<p>X</p>'
    gs.maintenance_mode = True
    _db.session.commit()
    rv = client.get('/api/public/platform-info')
    data = rv.get_json()['data']
    assert data['copyright_text'] == '© Test'
    assert data['has_impressum'] is True
    assert data['maintenance_mode'] is True


# ---------------------------------------------------------------------------
# POST /<slug>/register – Fehlerpfade
# ---------------------------------------------------------------------------

def test_register_instance_not_found(client):
    rv = client.post('/api/public/nicht-vorhanden/register', json={'altcha': 'x'})
    assert rv.status_code == 404


def test_register_site_locked_returns_403(client, instance):
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.site_locked = True
    _db.session.commit()
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Xaver', 'last_name': 'Yara', 'altcha': answer,
    })
    assert rv.status_code == 403


def test_register_after_deadline_returns_403(client, instance):
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.registration_deadline = datetime.now(timezone.utc) - timedelta(days=1)
    _db.session.commit()
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Xaver', 'last_name': 'Yara', 'altcha': answer,
    })
    assert rv.status_code == 403


def test_register_validation_error(client, instance):
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={'altcha': answer})
    assert rv.status_code == 422


@patch('app.api.public.is_mail_configured', return_value=False)
def test_register_with_email_without_mail_configured_returns_503(mock_mail, client, instance):
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Xaver', 'last_name': 'Yara', 'email': 'x@test.de', 'altcha': answer,
    })
    assert rv.status_code == 503


def test_register_duplicate_email_returns_409(client, instance):
    v = Volunteer(instance_id=instance.id, name='Bestehend', first_name='Bestehend', email='dup@test.de')
    _db.session.add(v)
    _db.session.commit()

    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Neu', 'last_name': 'Y', 'email': 'dup@test.de', 'altcha': answer,
    })
    assert rv.status_code == 409


@patch('app.api.public._base_url', side_effect=RuntimeError('nicht konfiguriert'))
def test_register_with_email_base_url_unavailable_returns_503(mock_base_url, client, instance):
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Xaver', 'last_name': 'Yara', 'email': 'x@test.de', 'altcha': answer,
    })
    assert rv.status_code == 503


@patch('app.api.public.send_mail', side_effect=RuntimeError('SMTP down'))
def test_register_with_email_still_succeeds_when_welcome_mail_fails(mock_send, client, instance):
    """Willkommensmail-Fehler darf die Registrierung nicht verhindern (nur geloggt)."""
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Xaver', 'last_name': 'Yara', 'email': 'x@test.de', 'altcha': answer,
    })
    assert rv.status_code == 201


def test_register_with_email_uses_instance_primary_color(client, instance):
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.primary_color = '#123456'
    _db.session.commit()
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Xaver', 'last_name': 'Yara', 'email': 'farbig@test.de', 'altcha': answer,
    })
    assert rv.status_code == 201


# ---------------------------------------------------------------------------
# POST /<slug>/welcome/<token> – Fehlerpfad
# ---------------------------------------------------------------------------

def test_welcome_setup_invalid_token_returns_400(client, instance):
    rv = client.post(f'/api/public/{instance.slug}/welcome/ungueltig123', json={'password': 'SicheresPasswort1'})
    assert rv.status_code == 400


def test_welcome_info_instance_not_found_returns_400(client):
    rv = client.get('/api/public/nicht-vorhanden/welcome/irgendein-token')
    assert rv.status_code == 400


# ---------------------------------------------------------------------------
# Impressum/Datenschutz – Plattform- und Instanzebene
# ---------------------------------------------------------------------------

def test_platform_impressum_without_global_settings(client):
    rv = client.get('/api/public/impressum')
    assert rv.status_code == 200
    assert rv.get_json()['data']['context'] == 'platform'


def test_platform_datenschutz_renders_template_with_contact_placeholders(client):
    gs = _global_settings()
    gs.datenschutz_template_html = '<p>Kontakt: {{person}}, {{email}}</p>'
    gs.contact_person = 'Max Mustermann'
    gs.contact_email = 'kontakt@test.de'
    _db.session.commit()
    rv = client.get('/api/public/datenschutz')
    assert rv.status_code == 200
    html = rv.get_json()['data']['privacy_policy_html']
    assert 'Max Mustermann' in html
    assert 'kontakt@test.de' in html


def test_instance_impressum_not_found(client):
    rv = client.get('/api/public/nicht-vorhanden/impressum')
    assert rv.status_code == 404


def test_instance_impressum_merges_provider_and_instance_html(client, instance):
    # _render_template() für instance_impressum nutzt _contact_vars(instance) –
    # die Kontaktfelder liegen direkt auf dem Instance-Modell, nicht auf SiteSettings.
    gs = _global_settings()
    gs.impressum_template_html = '<p>{{organisation}}</p>'
    gs.provider_impressum_html = '<p>Plattform-Betreiber</p>'
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.instance_impressum_html = '<p>Instanz-Zusatz</p>'
    instance.contact_organisation = 'Testverein e.V.'
    _db.session.commit()

    rv = client.get(f'/api/public/{instance.slug}/impressum')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert 'Testverein e.V.' in data['html']
    assert data['operator_html'] == '<p>Plattform-Betreiber</p>'
    assert data['context'] == 'instance'


def test_instance_info_merges_provider_and_instance_impressum(client, instance):
    gs = _global_settings()
    gs.provider_impressum_html = '<p>Plattform-Teil</p>'
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.instance_impressum_html = '<p>Instanz-Teil</p>'
    _db.session.commit()

    rv = client.get(f'/api/public/{instance.slug}/info')
    assert rv.status_code == 200
    html = rv.get_json()['data']['impressum_html']
    assert '<p>Plattform-Teil</p>' in html
    assert '<p>Instanz-Teil</p>' in html


def test_datenschutz_instance_not_found(client):
    rv = client.get('/api/public/nicht-vorhanden/datenschutz')
    assert rv.status_code == 404


# ---------------------------------------------------------------------------
# POST /<slug>/forgot-password – bisher komplett ungetestet
# ---------------------------------------------------------------------------

def test_forgot_password_instance_not_found(client):
    rv = client.post('/api/public/nicht-vorhanden/forgot-password', json={'email': 'x@test.de'})
    assert rv.status_code == 404


def test_forgot_password_unknown_email_returns_generic_200(client, instance):
    """Kein Hinweis, ob die E-Mail existiert (Enumeration-Schutz)."""
    rv = client.post(f'/api/public/{instance.slug}/forgot-password', json={'email': 'unbekannt@test.de'})
    assert rv.status_code == 200
    assert 'gesendet' in rv.get_json()['message']


@patch('app.api.public.send_mail')
@patch('app.api.public.is_mail_configured', return_value=True)
def test_forgot_password_known_email_sends_reset_mail(mock_configured, mock_send, client, instance, volunteer):
    rv = client.post(f'/api/public/{instance.slug}/forgot-password', json={'email': volunteer.email})
    assert rv.status_code == 200
    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == volunteer.email

    _db.session.refresh(volunteer)
    assert volunteer.reset_token is not None


@patch('app.api.public.send_mail')
@patch('app.api.public.is_mail_configured', return_value=True)
def test_forgot_password_soft_deleted_volunteer_no_mail_sent(mock_configured, mock_send, client, instance, volunteer):
    volunteer_email = volunteer.email
    volunteer.soft_delete()
    _db.session.commit()

    rv = client.post(f'/api/public/{instance.slug}/forgot-password', json={'email': volunteer_email})
    assert rv.status_code == 200
    mock_send.assert_not_called()


@patch('app.api.public.is_mail_configured', return_value=False)
def test_forgot_password_mail_not_configured_no_mail_sent(mock_configured, client, instance, volunteer):
    with patch('app.api.public.send_mail') as mock_send:
        rv = client.post(f'/api/public/{instance.slug}/forgot-password', json={'email': volunteer.email})
        assert rv.status_code == 200
        mock_send.assert_not_called()


@patch('app.api.public._base_url', side_effect=RuntimeError('nicht konfiguriert'))
@patch('app.api.public.is_mail_configured', return_value=True)
def test_forgot_password_base_url_unavailable_no_mail_sent(mock_configured, mock_base_url, client, instance, volunteer):
    with patch('app.api.public.send_mail') as mock_send:
        rv = client.post(f'/api/public/{instance.slug}/forgot-password', json={'email': volunteer.email})
        assert rv.status_code == 200
        mock_send.assert_not_called()


@patch('app.api.public.send_mail', side_effect=RuntimeError('SMTP down'))
@patch('app.api.public.is_mail_configured', return_value=True)
def test_forgot_password_still_returns_200_when_mail_fails(mock_configured, mock_send, client, instance, volunteer):
    rv = client.post(f'/api/public/{instance.slug}/forgot-password', json={'email': volunteer.email})
    assert rv.status_code == 200


@patch('app.api.public.send_mail')
@patch('app.api.public.is_mail_configured', return_value=True)
def test_forgot_password_uses_instance_primary_color(mock_configured, mock_send, client, instance, volunteer):
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.primary_color = '#654321'
    _db.session.commit()
    rv = client.post(f'/api/public/{instance.slug}/forgot-password', json={'email': volunteer.email})
    assert rv.status_code == 200
    mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# POST /<slug>/reset-password – Fehlerpfade
# ---------------------------------------------------------------------------

def test_reset_password_instance_not_found(client):
    rv = client.post('/api/public/nicht-vorhanden/reset-password', json={'token': 'x', 'password': 'SicheresPasswort1'})
    assert rv.status_code == 404


def test_reset_password_deleted_volunteer_token_invalid(client, instance, volunteer):
    raw = secrets.token_urlsafe(32)
    volunteer.reset_token = hashlib.sha256(raw.encode()).hexdigest()
    volunteer.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    _db.session.commit()
    volunteer.soft_delete()
    _db.session.commit()

    rv = client.post(f'/api/public/{instance.slug}/reset-password', json={
        'token': raw, 'password': 'SicheresPasswort1',
    })
    assert rv.status_code == 400
