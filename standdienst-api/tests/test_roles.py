"""Tests für das Drei-Rollen-System: Global-Admin, Instanz-Admin, Organisator."""
from app.extensions import db as _db
from tests.conftest import assign_organizer as _assign, login as _login


# ---------------------------------------------------------------------------
# Instanz-Admin – kann Site Settings bearbeiten
# ---------------------------------------------------------------------------

def test_instance_admin_can_read_settings(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/settings')
    assert rv.status_code == 200


def test_instance_admin_can_update_settings(client, instance, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/settings',
                    json={'site_title': 'Geändert'})
    assert rv.status_code == 200
    assert rv.get_json()['data']['site_title'] == 'Geändert'


# ---------------------------------------------------------------------------
# Einfacher Organisator – kann Site Settings NICHT bearbeiten
# ---------------------------------------------------------------------------

def test_organizer_cannot_update_settings(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/settings',
                    json={'site_title': 'Hack'})
    assert rv.status_code == 403


def test_organizer_cannot_read_settings(client, instance, organizer_user):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/settings')
    assert rv.status_code == 403


# ---------------------------------------------------------------------------
# Einfacher Organisator – kann operative Daten lesen
# ---------------------------------------------------------------------------

def test_organizer_can_list_volunteers(client, instance, organizer_user, volunteer):
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.get(f'/api/admin/{instance.slug}/volunteers')
    assert rv.status_code == 200


# ---------------------------------------------------------------------------
# Global-Admin – kann alles
# ---------------------------------------------------------------------------

def test_global_admin_can_update_settings(client, instance, admin_user):
    _login(client, admin_user.email)
    rv = client.put(f'/api/admin/{instance.slug}/settings',
                    json={'site_title': 'Admin-Titel'})
    assert rv.status_code == 200


# ---------------------------------------------------------------------------
# Soft-Delete & permanentes Löschen
# ---------------------------------------------------------------------------

def test_soft_delete_pseudonymizes_volunteer(client, instance, volunteer, admin_user):
    _login(client, admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}')
    assert rv.status_code == 204
    _db.session.refresh(volunteer)
    assert volunteer.name == f'[gelöscht-{volunteer.id}]'
    assert volunteer.email is None
    assert volunteer.deleted_at is not None


def test_soft_deleted_volunteer_cannot_login(client, instance, volunteer):
    _db.session.refresh(volunteer)
    volunteer.soft_delete()
    _db.session.commit()

    rv = client.post('/api/auth/volunteer-login', json={
        'slug': instance.slug, 'email': 'helfer@test.de', 'password': 'TestPass1!',
    })
    assert rv.status_code == 401


def test_permanent_delete_by_global_admin(client, instance, volunteer, admin_user):
    _login(client, admin_user.email)
    vid = volunteer.id
    rv = client.delete(f'/api/admin/{instance.slug}/volunteers/{vid}/permanent')
    assert rv.status_code == 204
    assert _db.session.get(type(volunteer), vid) is None


def test_permanent_delete_denied_for_instance_admin(client, instance, volunteer, instance_admin_user):
    _assign(instance_admin_user, instance)
    _login(client, instance_admin_user.email)
    rv = client.delete(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}/permanent')
    assert rv.status_code == 403


def test_optimistic_lock_volunteer_update(client, instance, admin_user):
    from app.models import Volunteer
    from app.extensions import db as _db
    from datetime import datetime, timezone, timedelta

    v = Volunteer(
        instance_id=instance.id,
        name='Locktest Volunteer',
        first_name='Lock',
        last_name='Test',
    )
    _db.session.add(v)
    _db.session.commit()

    # Login als Admin
    client.post('/api/auth/login', json={'email': admin_user.email, 'password': 'TestPass1!'})

    # Stale updated_at senden
    stale_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    rv = client.put(
        f'/api/admin/{instance.slug}/volunteers/{v.id}',
        json={'first_name': 'Conflict', 'updated_at': stale_ts},
    )
    assert rv.status_code == 409
