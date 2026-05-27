"""Tests für DSGVO-Funktionen: Datenauskunft, Soft-Delete."""
from app.extensions import db as _db
from app.models import GlobalSettings


def _volunteer_login(client, instance, volunteer):
    rv = client.post('/api/auth/volunteer-login', json={
        'slug': instance.slug, 'email': volunteer.email, 'password': 'TestPass1!',
    })
    assert rv.status_code == 200
    return rv


def test_meine_daten_returns_volunteer_info(client, instance, volunteer):
    _volunteer_login(client, instance, volunteer)
    rv = client.get(f'/api/volunteer/{instance.slug}/meine-daten')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['volunteer']['email'] == volunteer.email
    assert data['volunteer']['name'] == volunteer.name
    assert 'registrations' in data


def test_meine_daten_requires_auth(client, instance):
    rv = client.get(f'/api/volunteer/{instance.slug}/meine-daten')
    assert rv.status_code == 401


def test_self_soft_delete(client, instance, volunteer):
    _volunteer_login(client, instance, volunteer)
    rv = client.delete(f'/api/volunteer/{instance.slug}/profile')
    assert rv.status_code == 204
    _db.session.refresh(volunteer)
    assert volunteer.deleted_at is not None
    assert f'[gelöscht-{volunteer.id}]' == volunteer.name
    assert volunteer.email is None


def test_datenschutz_route_returns_policy(client, instance):
    gs = GlobalSettings.query.first()
    if not gs:
        gs = GlobalSettings()
        _db.session.add(gs)
    gs.datenschutz_template_html = '<p>Unsere Datenschutzerklärung</p>'
    _db.session.commit()

    rv = client.get(f'/api/public/{instance.slug}/datenschutz')
    assert rv.status_code == 200
    assert 'Datenschutz' in rv.get_json()['data']['privacy_policy_html']


def test_instance_info_exposes_has_privacy_policy(client, instance):
    rv = client.get(f'/api/public/{instance.slug}/info')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert 'has_privacy_policy' in data
