"""Tests für Pagination-Limits in Admin-Endpunkten."""
from app.extensions import db as _db
from app.models import Admin, Instance, SiteSettings


def _admin_login(client):
    admin = Admin(email='padmin@test.de', is_primary=True)
    admin.set_password('TestPass1!')
    _db.session.add(admin)
    _db.session.commit()
    rv = client.post('/api/auth/login', json={'email': 'padmin@test.de', 'password': 'TestPass1!'})
    assert rv.status_code == 200


def _make_instance():
    inst = Instance(slug='pg-test', name='PagTest')
    _db.session.add(inst)
    _db.session.flush()
    _db.session.add(SiteSettings(instance_id=inst.id))
    _db.session.commit()
    return inst


def test_activity_per_page_capped(client):
    _admin_login(client)
    rv = client.get('/api/admin/activity?per_page=99999')
    assert rv.status_code == 200
    assert rv.get_json()['per_page'] <= 500


def test_volunteers_per_page_capped(client):
    _admin_login(client)
    inst = _make_instance()
    rv = client.get(f'/api/admin/{inst.slug}/volunteers?per_page=99999')
    assert rv.status_code == 200
    assert rv.get_json()['per_page'] <= 500


def test_page_minimum_is_one(client):
    _admin_login(client)
    rv = client.get('/api/admin/activity?page=0')
    assert rv.status_code == 200
    assert rv.get_json()['page'] >= 1


def test_negative_per_page_sanitized(client):
    _admin_login(client)
    rv = client.get('/api/admin/activity?per_page=-1')
    assert rv.status_code == 200
    assert rv.get_json()['per_page'] >= 1
