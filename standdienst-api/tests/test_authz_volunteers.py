"""Autorisierungstests für app/api/admin/volunteers.py.

list/detail/create/update: @require_staff (Organisator darf anlegen und bearbeiten, nur eigene Instanz)
Passwort setzen beim Anlegen/Bearbeiten: nur Instanz-Admin/Global-Admin
delete/dsgvo-auskunft/reset-password: @require_instance_admin
"""
from app.extensions import db as _db
from app.models import Volunteer
from tests.conftest import assign_organizer as _assign, login as _login


def _make_volunteer(instance, email='v@test.de'):
    v = Volunteer(instance_id=instance.id, name='Max Muster', first_name='Max', last_name='Muster', email=email)
    _db.session.add(v)
    _db.session.commit()
    return v


def _as_organizer(client, organizer_user, instance):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)


def test_organizer_can_create_without_password(client, instance, organizer_user):
    _as_organizer(client, organizer_user, instance)
    rv = client.post(f'/api/admin/{instance.slug}/volunteers', json={'first_name': 'Erika', 'last_name': 'Neu'})
    assert rv.status_code == 201
    assert rv.get_json()['data']['first_name'] == 'Erika'


def test_organizer_cannot_create_with_password(client, instance, organizer_user):
    _as_organizer(client, organizer_user, instance)
    rv = client.post(f'/api/admin/{instance.slug}/volunteers', json={
        'first_name': 'Erika', 'email': 'erika@test.de', 'password': 'Geheim123!',
    })
    assert rv.status_code == 403
    assert _db.session.query(Volunteer).filter_by(email='erika@test.de').first() is None


def test_organizer_can_update_name_and_email(client, instance, organizer_user):
    v = _make_volunteer(instance)
    _as_organizer(client, organizer_user, instance)
    rv = client.put(f'/api/admin/{instance.slug}/volunteers/{v.id}', json={
        'first_name': 'Moritz', 'email': 'moritz@test.de', 'updated_at': v.updated_at.isoformat(),
    })
    assert rv.status_code == 200
    assert rv.get_json()['data']['email'] == 'moritz@test.de'


def test_organizer_cannot_set_password_on_update(client, instance, organizer_user):
    v = _make_volunteer(instance)
    _as_organizer(client, organizer_user, instance)
    rv = client.put(f'/api/admin/{instance.slug}/volunteers/{v.id}', json={
        'password': 'Geheim123!', 'updated_at': v.updated_at.isoformat(),
    })
    assert rv.status_code == 403
    _db.session.refresh(v)
    assert not v.has_login


def test_organizer_cannot_delete(client, instance, organizer_user):
    v = _make_volunteer(instance)
    _as_organizer(client, organizer_user, instance)
    rv = client.delete(f'/api/admin/{instance.slug}/volunteers/{v.id}')
    assert rv.status_code == 403


def test_organizer_cannot_send_dsgvo_auskunft(client, instance, organizer_user):
    v = _make_volunteer(instance)
    _as_organizer(client, organizer_user, instance)
    rv = client.post(f'/api/admin/{instance.slug}/volunteers/{v.id}/dsgvo-auskunft')
    assert rv.status_code == 403


def test_organizer_cannot_reset_password(client, instance, organizer_user):
    v = _make_volunteer(instance)
    _as_organizer(client, organizer_user, instance)
    rv = client.post(f'/api/admin/{instance.slug}/volunteers/{v.id}/reset-password')
    assert rv.status_code == 403


def test_organizer_of_other_instance_cannot_create(client, instance, other_instance, organizer_user):
    _assign(organizer_user, other_instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/volunteers', json={'first_name': 'Fremd'})
    assert rv.status_code == 403


def test_organizer_cannot_update_volunteer_of_other_instance(client, instance, other_instance, organizer_user):
    foreign = _make_volunteer(other_instance)
    _as_organizer(client, organizer_user, instance)
    rv = client.put(f'/api/admin/{instance.slug}/volunteers/{foreign.id}', json={
        'first_name': 'Fremd', 'updated_at': foreign.updated_at.isoformat(),
    })
    assert rv.status_code == 404


def test_instance_admin_can_create_with_password(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/volunteers', json={
        'first_name': 'Erika', 'email': 'erika@test.de', 'password': 'Geheim123!',
    })
    assert rv.status_code == 201
