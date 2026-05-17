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


def test_captcha(client, instance):
    rv = client.get(f'/api/public/{instance.slug}/captcha')
    assert rv.status_code == 200
    assert 'question' in rv.get_json()
