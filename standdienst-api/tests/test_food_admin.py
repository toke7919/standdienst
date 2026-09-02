"""Funktionale Tests für app/api/admin/food.py.

Autorisierung (@require_staff/@require_instance_admin, Instanz-Zugriffsschutz)
ist bereits in test_authz_food.py abgedeckt. test_admin_food.py deckt bereits
Grundlegendes von list_food_types (Sortierung, event_date_formatted) ab. Hier
geht es um CRUD-Geschäftslogik: Validierung, Optimistic Locking, Filter,
Aktivitätslog beim Admin-Eintragen von Spenden.
"""
from datetime import date, datetime, timezone, timedelta

from app.extensions import db as _db
from app.models import EventDate, FoodDonationType, FoodDonation, ActivityLog
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


def _make_event_date(instance, day=date(2026, 9, 1)):
    ed = EventDate(instance_id=instance.id, date=day, is_draft=False)
    _db.session.add(ed)
    _db.session.commit()
    return ed


def _make_food_type(instance, ed=None, name='Kuchen'):
    ed = ed or _make_event_date(instance)
    ft = FoodDonationType(
        instance_id=instance.id, event_date_id=ed.id, name=name,
        delivery_datetime=datetime.now(timezone.utc), delivery_location='Küche',
    )
    _db.session.add(ft)
    _db.session.commit()
    return ft


# ---------------------------------------------------------------------------
# GET /food-types
# ---------------------------------------------------------------------------

def test_list_food_types_filters_by_date_id(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ed1 = _make_event_date(instance, date(2026, 9, 1))
    ed2 = _make_event_date(instance, date(2026, 9, 2))
    _make_food_type(instance, ed1, name='Kuchen')
    _make_food_type(instance, ed2, name='Salat')

    rv = c.get(f'/api/admin/{instance.slug}/food-types?date_id={ed1.id}')
    assert rv.status_code == 200
    names = [t['name'] for t in rv.get_json()['data']]
    assert names == ['Kuchen']


# ---------------------------------------------------------------------------
# POST /food-types
# ---------------------------------------------------------------------------

def test_create_food_type_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/food-types', json={})
    assert rv.status_code == 422


def test_create_food_type_event_date_not_found(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/food-types', json={
        'event_date_id': 99999, 'name': 'Kuchen',
        'delivery_datetime': datetime.now(timezone.utc).isoformat(), 'delivery_location': 'Küche',
    })
    assert rv.status_code == 404


def test_create_food_type_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ed = _make_event_date(instance)
    rv = c.post(f'/api/admin/{instance.slug}/food-types', json={
        'event_date_id': ed.id, 'name': 'Kuchen', 'refrigeration_enabled': True,
        'delivery_datetime': datetime.now(timezone.utc).isoformat(), 'delivery_location': 'Küche',
    })
    assert rv.status_code == 201
    assert rv.get_json()['data']['name'] == 'Kuchen'


# ---------------------------------------------------------------------------
# PUT /food-types/<id>
# ---------------------------------------------------------------------------

def test_update_food_type_not_found(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/food-types/99999', json={'name': 'X'})
    assert rv.status_code == 404


def test_update_food_type_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ft = _make_food_type(instance)
    rv = c.put(f'/api/admin/{instance.slug}/food-types/{ft.id}', json={'name': ''})
    assert rv.status_code == 422


def test_update_food_type_optimistic_lock_conflict(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ft = _make_food_type(instance)
    stale = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rv = c.put(f'/api/admin/{instance.slug}/food-types/{ft.id}', json={
        'name': 'Neuer Name', 'updated_at': stale,
    })
    assert rv.status_code == 409


def test_update_food_type_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ft = _make_food_type(instance)
    rv = c.put(f'/api/admin/{instance.slug}/food-types/{ft.id}', json={'name': 'Umbenannt'})
    assert rv.status_code == 200
    assert rv.get_json()['data']['name'] == 'Umbenannt'


# ---------------------------------------------------------------------------
# DELETE /food-types/<id>
# ---------------------------------------------------------------------------

def test_delete_food_type_not_found(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.delete(f'/api/admin/{instance.slug}/food-types/99999')
    assert rv.status_code == 404


def test_delete_food_type_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ft = _make_food_type(instance)
    ft_id = ft.id
    rv = c.delete(f'/api/admin/{instance.slug}/food-types/{ft_id}')
    assert rv.status_code == 204
    assert _db.session.get(FoodDonationType, ft_id) is None


# ---------------------------------------------------------------------------
# GET /food-donations
# ---------------------------------------------------------------------------

def test_list_food_donations_filters_by_type_id(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ft1 = _make_food_type(instance, _make_event_date(instance, date(2026, 9, 1)), name='Kuchen')
    ft2 = _make_food_type(instance, _make_event_date(instance, date(2026, 9, 2)), name='Salat')
    _db.session.add_all([
        FoodDonation(guest_name='Gast 1', food_type_id=ft1.id, description='Apfelkuchen'),
        FoodDonation(guest_name='Gast 2', food_type_id=ft2.id, description='Nudelsalat'),
    ])
    _db.session.commit()

    rv = c.get(f'/api/admin/{instance.slug}/food-donations?type_id={ft1.id}')
    assert rv.status_code == 200
    body = rv.get_json()
    assert body['total'] == 1
    assert body['data'][0]['description'] == 'Apfelkuchen'


# ---------------------------------------------------------------------------
# POST /food-donations
# ---------------------------------------------------------------------------

def test_create_food_donation_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/food-donations', json={})
    assert rv.status_code == 422


def test_create_food_donation_type_not_found(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/food-donations', json={
        'guest_name': 'Gast', 'food_type_id': 99999, 'description': 'Kuchen',
    })
    assert rv.status_code == 404


def test_create_food_donation_success_logs_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ft = _make_food_type(instance, name='Kuchen')
    rv = c.post(f'/api/admin/{instance.slug}/food-donations', json={
        'guest_name': 'Gast Meier', 'food_type_id': ft.id, 'description': 'Apfelkuchen',
        'needs_refrigeration': True,
    })
    assert rv.status_code == 201
    data = rv.get_json()['data']
    assert data['needs_refrigeration'] is True

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.FOOD_REGISTER).first()
    assert log is not None
    assert 'Admin-Eintragung' in log.details
    assert log.volunteer_name == 'Gast Meier'


# ---------------------------------------------------------------------------
# PUT /food-donations/<id>
# ---------------------------------------------------------------------------

def test_update_food_donation_not_found(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/food-donations/99999', json={'description': 'X'})
    assert rv.status_code == 404


def test_update_food_donation_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ft = _make_food_type(instance)
    donation = FoodDonation(guest_name='Gast', food_type_id=ft.id, description='Kuchen')
    _db.session.add(donation)
    _db.session.commit()

    rv = c.put(f'/api/admin/{instance.slug}/food-donations/{donation.id}', json={'description': ''})
    assert rv.status_code == 422


def test_update_food_donation_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ft = _make_food_type(instance)
    donation = FoodDonation(guest_name='Gast', food_type_id=ft.id, description='Kuchen')
    _db.session.add(donation)
    _db.session.commit()

    rv = c.put(f'/api/admin/{instance.slug}/food-donations/{donation.id}', json={
        'description': 'Schokokuchen', 'needs_refrigeration': True,
    })
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['description'] == 'Schokokuchen'
    assert data['needs_refrigeration'] is True


# ---------------------------------------------------------------------------
# DELETE /food-donations/<id>
# ---------------------------------------------------------------------------

def test_delete_food_donation_not_found(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.delete(f'/api/admin/{instance.slug}/food-donations/99999')
    assert rv.status_code == 404


def test_delete_food_donation_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ft = _make_food_type(instance)
    donation = FoodDonation(guest_name='Gast', food_type_id=ft.id, description='Kuchen')
    _db.session.add(donation)
    _db.session.commit()
    donation_id = donation.id

    rv = c.delete(f'/api/admin/{instance.slug}/food-donations/{donation_id}')
    assert rv.status_code == 204
    assert _db.session.get(FoodDonation, donation_id) is None
