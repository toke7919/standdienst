def test_list_instances(client, instance):
    rv = client.get('/api/public/instances')
    assert rv.status_code == 200
    slugs = [i['slug'] for i in rv.get_json()['data']]
    assert instance.slug in slugs


def test_instance_info(client, instance):
    rv = client.get(f'/api/public/{instance.slug}/info')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['slug'] == instance.slug


def test_instance_info_not_found(client):
    rv = client.get('/api/public/nicht-vorhanden/info')
    assert rv.status_code == 404


def test_datenschutz_escapes_contact_fields(client, instance):
    """Kontaktfeld-Werte werden HTML-escaped in die Datenschutz-Vorlage eingesetzt (kein XSS)."""
    from app.extensions import db as _db
    from app.models import GlobalSettings, Instance

    _db.session.add(GlobalSettings(datenschutz_template_html='<p>Kontakt: {{person}}</p>'))
    inst = _db.session.get(Instance, instance.id)
    inst.contact_person = '<script>alert(1)</script>'
    _db.session.commit()

    rv = client.get(f'/api/public/{instance.slug}/datenschutz')
    assert rv.status_code == 200
    html = rv.get_json()['data']['privacy_policy_html']
    assert '<script>' not in html
    assert '&lt;script&gt;' in html


def test_spa_html_has_csp_header(client):
    """Das ausgelieferte SPA-Dokument trägt eine restriktive Content-Security-Policy."""
    import pytest
    rv = client.get('/')
    if 'text/html' not in (rv.content_type or ''):
        pytest.skip('Frontend nicht gebaut – SPA-Dokument nicht verfügbar')
    csp = rv.headers.get('Content-Security-Policy', '')
    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_captcha(client, instance):
    rv = client.get(f'/api/public/{instance.slug}/captcha')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['algorithm'] == 'SHA-256'
    assert 'challenge' in data
    assert 'salt' in data
    assert 'signature' in data
    assert 'maxnumber' in data
