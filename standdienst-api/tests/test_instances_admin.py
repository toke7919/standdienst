"""Funktionale Tests für app/api/admin/instances.py.

Autorisierung (@require_admin für create/get/update/delete, @require_staff
+ Datenscoping für list, @require_staff + Inline-Admin-Prüfung für
clear_instance_data) ist bereits in test_authz_instances.py abgedeckt. Hier
geht es um Validierung, Duplikat-Schutz, SiteSettings-Erstellung/-Update
(inkl. branding_enabled + Cache-Invalidierung) und die clear-data-Kaskade.
"""
from datetime import date, time, datetime, timezone

from app.extensions import db as _db
from app.models import (
    Instance, SiteSettings, ActivityLog, Stand, EventDate, Shift,
    Registration, Volunteer, FoodDonationType, FoodDonation,
)
from app.utils.settings_cache import _cache
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


# ---------------------------------------------------------------------------
# GET /instances
# ---------------------------------------------------------------------------

def test_list_instances_global_admin_sees_all(client, admin_user, instance, other_instance):
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/instances')
    assert rv.status_code == 200
    slugs = {i['slug'] for i in rv.get_json()['data']}
    assert {instance.slug, other_instance.slug} <= slugs


# ---------------------------------------------------------------------------
# POST /instances
# ---------------------------------------------------------------------------

def test_create_instance_validation_error(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/instances', json={})
    assert rv.status_code == 422


def test_create_instance_duplicate_slug_returns_409(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/instances', json={'slug': instance.slug, 'name': 'Andere'})
    assert rv.status_code == 409


def test_create_instance_creates_site_settings_and_activity_log(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/instances', json={'slug': 'neue-instanz', 'name': 'Neue Instanz'})
    assert rv.status_code == 201
    new_id = rv.get_json()['data']['id']

    settings = _db.session.query(SiteSettings).filter_by(instance_id=new_id).first()
    assert settings is not None

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Instanz angelegt' in log.details


# ---------------------------------------------------------------------------
# GET /instances/<id>
# ---------------------------------------------------------------------------

def test_get_instance_not_found(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/instances/99999')
    assert rv.status_code == 404


def test_get_instance_returns_data(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.get(f'/api/admin/instances/{instance.id}')
    assert rv.status_code == 200
    assert rv.get_json()['data']['slug'] == instance.slug


# ---------------------------------------------------------------------------
# PUT /instances/<id>
# ---------------------------------------------------------------------------

def test_update_instance_not_found(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.put('/api/admin/instances/99999', json={'name': 'X'})
    assert rv.status_code == 404


def test_update_instance_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/instances/{instance.id}', json={'name': ''})
    assert rv.status_code == 422


def test_update_instance_name_and_activity_log(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/instances/{instance.id}', json={'name': 'Neuer Name'})
    assert rv.status_code == 200
    assert rv.get_json()['data']['name'] == 'Neuer Name'

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Instanz geändert' in log.details


def test_update_instance_branding_enabled_updates_site_settings_and_invalidates_cache(client, admin_user, instance):
    _cache[f's:{instance.id}'] = ('irgendein-alter-wert', 9999999999.0)
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/instances/{instance.id}', json={'branding_enabled': False})
    assert rv.status_code == 200

    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    assert settings.branding_enabled is False
    assert f's:{instance.id}' not in _cache


def test_update_instance_without_branding_enabled_leaves_site_settings_unchanged(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/instances/{instance.id}', json={'name': 'Ohne Branding-Änderung'})
    assert rv.status_code == 200
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    assert settings.branding_enabled is True  # Default unverändert


# ---------------------------------------------------------------------------
# DELETE /instances/<id>
# ---------------------------------------------------------------------------

def test_delete_instance_not_found(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.delete('/api/admin/instances/99999')
    assert rv.status_code == 404


def test_delete_instance_success_logs_global_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    instance_id = instance.id
    rv = c.delete(f'/api/admin/instances/{instance_id}')
    assert rv.status_code == 204
    assert _db.session.get(Instance, instance_id) is None

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert log.instance_id is None  # globaler Log-Eintrag, da Instanz weg ist
    assert instance.slug in log.details


# ---------------------------------------------------------------------------
# DELETE /<slug>/clear-data
# ---------------------------------------------------------------------------

def test_clear_instance_data_removes_all_related_records(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)

    stand = Stand(instance_id=instance.id, name='Stand')
    _db.session.add(stand)
    _db.session.flush()
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    shift = Shift(stand_id=stand.id, event_date_id=ed.id, start_time=time(10, 0), end_time=time(12, 0))
    _db.session.add(shift)
    _db.session.flush()
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    ft = FoodDonationType(instance_id=instance.id, event_date_id=ed.id, name='Kuchen',
                          delivery_datetime=datetime.now(timezone.utc), delivery_location='Küche')
    _db.session.add(ft)
    _db.session.flush()
    _db.session.add(FoodDonation(volunteer_id=volunteer.id, food_type_id=ft.id, description='Kuchen'))
    _db.session.commit()

    rv = c.delete(f'/api/admin/{instance.slug}/clear-data')
    assert rv.status_code == 204

    assert _db.session.query(Registration).count() == 0
    assert _db.session.query(FoodDonation).count() == 0
    assert _db.session.query(FoodDonationType).count() == 0
    assert _db.session.query(Shift).count() == 0
    assert _db.session.query(Stand).count() == 0
    assert _db.session.query(EventDate).count() == 0
    assert _db.session.query(Volunteer).count() == 0
    # Instanz selbst und ihre SiteSettings bleiben erhalten
    assert _db.session.get(Instance, instance.id) is not None

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Alle Instanzdaten gelöscht' in log.details


def test_clear_instance_data_does_not_affect_other_instance(client, admin_user, instance, other_instance):
    c = _admin_client(client, admin_user)
    foreign_stand = Stand(instance_id=other_instance.id, name='Fremd')
    _db.session.add(foreign_stand)
    _db.session.commit()

    rv = c.delete(f'/api/admin/{instance.slug}/clear-data')
    assert rv.status_code == 204
    assert _db.session.get(Stand, foreign_stand.id) is not None
