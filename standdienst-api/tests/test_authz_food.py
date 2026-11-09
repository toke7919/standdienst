"""Autorisierungstests für app/api/admin/food.py.

list_food_types/list_food_donations: @require_staff (Organisator darf lesen)
create/update/delete (Typen & Spenden): @require_staff (Organisator darf schreiben, nur eigene Instanz)
"""
from datetime import date as _date, datetime as _dt, timezone as _tz
from app.extensions import db as _db
from app.models import EventDate, FoodDonation, FoodDonationType
from tests.conftest import assign_organizer as _assign, login as _login


def _make_date(instance):
    d = EventDate(instance_id=instance.id, date=_date(2027, 1, 1))
    _db.session.add(d)
    _db.session.commit()
    return d


def _make_food_type(instance, event_date=None):
    event_date = event_date or _make_date(instance)
    ft = FoodDonationType(
        instance_id=instance.id, event_date_id=event_date.id, name='Kuchen',
        delivery_datetime=_dt(2027, 1, 1, 10, 0, tzinfo=_tz.utc), delivery_location='Eingang',
    )
    _db.session.add(ft)
    _db.session.commit()
    return ft


def _make_donation(instance, food_type=None):
    food_type = food_type or _make_food_type(instance)
    d = FoodDonation(food_type_id=food_type.id, guest_name='Gast', description='Kuchen')
    _db.session.add(d)
    _db.session.commit()
    return d


def test_unauthenticated_rejected(client, instance):
    rv = client.get(f'/api/admin/{instance.slug}/food-types')
    assert rv.status_code == 401


def test_organizer_can_list_food_types(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/food-types')
    assert rv.status_code == 200


def test_organizer_can_list_donations(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/food-donations')
    assert rv.status_code == 200


def test_organizer_can_create_food_type(client, instance, organizer_user):
    d = _make_date(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/food-types', json={
        'event_date_id': d.id, 'name': 'Salat',
        'delivery_datetime': '2027-01-01T10:00:00+00:00', 'delivery_location': 'Eingang',
    })
    assert rv.status_code == 201


def test_organizer_can_update_food_type(client, instance, organizer_user):
    ft = _make_food_type(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/food-types/{ft.id}', json={'name': 'Torte', 'updated_at': ft.updated_at.isoformat()})
    assert rv.status_code == 200
    assert rv.get_json()['data']['name'] == 'Torte'


def test_organizer_can_delete_food_type(client, instance, organizer_user):
    ft = _make_food_type(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/food-types/{ft.id}')
    assert rv.status_code == 204


def test_organizer_can_create_donation(client, instance, organizer_user):
    ft = _make_food_type(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.post(f'/api/admin/{instance.slug}/food-donations', json={
        'guest_name': 'Gast', 'food_type_id': ft.id, 'description': 'Apfelkuchen',
    })
    assert rv.status_code == 201


def test_organizer_can_update_donation(client, instance, organizer_user):
    donation = _make_donation(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/food-donations/{donation.id}', json={'guest_name': 'Neuer Gast'})
    assert rv.status_code == 200


def test_organizer_can_delete_donation(client, instance, organizer_user):
    donation = _make_donation(instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/food-donations/{donation.id}')
    assert rv.status_code == 204


def test_instance_admin_can_delete_donation(client, instance, instance_admin_user):
    donation = _make_donation(instance)
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/food-donations/{donation.id}')
    assert rv.status_code == 204


def test_instance_admin_cannot_access_donation_of_other_instance(client, instance, other_instance, instance_admin_user):
    foreign_donation = _make_donation(other_instance)
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/food-donations/{foreign_donation.id}')
    assert rv.status_code == 404


def test_instance_admin_cannot_access_food_type_of_other_instance(client, instance, other_instance, instance_admin_user):
    foreign_type = _make_food_type(other_instance)
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/food-types/{foreign_type.id}')
    assert rv.status_code == 404


def test_organizer_of_other_instance_cannot_delete_donation(client, instance, other_instance, organizer_user):
    donation = _make_donation(instance)
    _assign(organizer_user, other_instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/food-donations/{donation.id}')
    assert rv.status_code == 403


def test_organizer_cannot_access_food_type_of_other_instance(client, instance, other_instance, organizer_user):
    foreign_type = _make_food_type(other_instance)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/food-types/{foreign_type.id}')
    assert rv.status_code == 404
