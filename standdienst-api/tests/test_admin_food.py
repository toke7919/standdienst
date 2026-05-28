import pytest
from datetime import date, datetime, timezone


@pytest.fixture
def food_admin_client(client):
    from app.models import Admin, GlobalSettings
    from app.extensions import db as _db
    admin = Admin(email='foodadmin@test.de', is_primary=True)
    admin.set_password('TestPass1!')
    _db.session.add(admin)
    gs = GlobalSettings(setup_complete=True)
    _db.session.add(gs)
    _db.session.commit()
    rv = client.post('/api/auth/login', json={'email': 'foodadmin@test.de', 'password': 'TestPass1!'})
    assert rv.status_code == 200
    return client


@pytest.fixture
def food_setup(food_admin_client, instance):
    from app.models import EventDate, FoodDonationType
    from app.extensions import db as _db
    date1 = EventDate(instance_id=instance.id, date=date(2026, 9, 1), label='Herbstfest', is_draft=False)
    date2 = EventDate(instance_id=instance.id, date=date(2026, 8, 1), is_draft=False)
    _db.session.add_all([date1, date2])
    _db.session.flush()
    ft1 = FoodDonationType(
        instance_id=instance.id,
        event_date_id=date1.id,
        name='Kuchen',
        refrigeration_enabled=False,
        delivery_datetime=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        delivery_location='Festplatz',
    )
    ft2 = FoodDonationType(
        instance_id=instance.id,
        event_date_id=date2.id,
        name='Salat',
        refrigeration_enabled=True,
        delivery_datetime=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        delivery_location='Küche',
    )
    _db.session.add_all([ft1, ft2])
    _db.session.commit()
    return {'instance': instance, 'types': [ft1, ft2]}


def test_food_types_include_event_date_formatted(food_admin_client, food_setup):
    """`event_date_formatted` und `event_date_label` werden in der API-Antwort zurückgegeben."""
    instance = food_setup['instance']
    rv = food_admin_client.get(f'/api/admin/{instance.slug}/food-types')
    assert rv.status_code == 200
    items = rv.get_json()['data']
    for item in items:
        assert 'event_date_formatted' in item
        assert item['event_date_formatted'] is not None


def test_food_types_sorted_chronologically(food_admin_client, food_setup):
    """Kategorien sind nach Termin-Datum sortiert (ältester Termin zuerst)."""
    instance = food_setup['instance']
    rv = food_admin_client.get(f'/api/admin/{instance.slug}/food-types')
    assert rv.status_code == 200
    items = rv.get_json()['data']
    assert len(items) == 2
    # ft2 hat Termin 2026-08-01, ft1 hat 2026-09-01 → Salat vor Kuchen
    assert items[0]['name'] == 'Salat'
    assert items[1]['name'] == 'Kuchen'
