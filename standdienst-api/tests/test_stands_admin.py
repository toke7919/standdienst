"""Funktionale Tests für app/api/admin/stands.py.

Autorisierung (@require_staff/@require_instance_admin, Instanz-Zugriffsschutz)
ist bereits in test_authz_stands.py abgedeckt. Hier geht es um Validierung,
Optimistic Locking, Reorder-Logik und Aktivitätslog-Details.
"""
from datetime import datetime, timezone, timedelta

from app.extensions import db as _db
from app.models import Stand, ActivityLog
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


def _make_stand(instance, name='Stand', sort_order=0):
    stand = Stand(instance_id=instance.id, name=name, sort_order=sort_order)
    _db.session.add(stand)
    _db.session.commit()
    return stand


# ---------------------------------------------------------------------------
# GET /stands
# ---------------------------------------------------------------------------

def test_list_stands_ordered_by_sort_order(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    _make_stand(instance, name='Zweiter', sort_order=1)
    _make_stand(instance, name='Erster', sort_order=0)

    rv = c.get(f'/api/admin/{instance.slug}/stands')
    assert rv.status_code == 200
    names = [s['name'] for s in rv.get_json()['data']]
    assert names == ['Erster', 'Zweiter']


# ---------------------------------------------------------------------------
# POST /stands
# ---------------------------------------------------------------------------

def test_create_stand_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/stands', json={})
    assert rv.status_code == 422


def test_create_stand_success_logs_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/stands', json={
        'name': 'Grillstand', 'description': 'Am Eingang',
    })
    assert rv.status_code == 201
    data = rv.get_json()['data']
    assert data['name'] == 'Grillstand'
    assert data['description'] == 'Am Eingang'

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Stand angelegt: Grillstand' in log.details


# ---------------------------------------------------------------------------
# PUT /stands/<id>
# ---------------------------------------------------------------------------

def test_update_stand_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/stands/99999', json={'name': 'X'})
    assert rv.status_code == 404


def test_update_stand_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    stand = _make_stand(instance)
    rv = c.put(f'/api/admin/{instance.slug}/stands/{stand.id}', json={'name': ''})
    assert rv.status_code == 422


def test_update_stand_optimistic_lock_conflict(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    stand = _make_stand(instance)
    stale = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rv = c.put(f'/api/admin/{instance.slug}/stands/{stand.id}', json={
        'name': 'Neuer Name', 'updated_at': stale,
    })
    assert rv.status_code == 409


def test_update_stand_success_logs_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    stand = _make_stand(instance, name='Alt')
    rv = c.put(f'/api/admin/{instance.slug}/stands/{stand.id}', json={'name': 'Neu'})
    assert rv.status_code == 200
    assert rv.get_json()['data']['name'] == 'Neu'

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Stand geändert: Neu' in log.details


# ---------------------------------------------------------------------------
# DELETE /stands/<id>
# ---------------------------------------------------------------------------

def test_delete_stand_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.delete(f'/api/admin/{instance.slug}/stands/99999')
    assert rv.status_code == 404


def test_delete_stand_success_logs_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    stand = _make_stand(instance, name='Zu löschen')
    stand_id = stand.id
    rv = c.delete(f'/api/admin/{instance.slug}/stands/{stand_id}')
    assert rv.status_code == 204
    assert _db.session.get(Stand, stand_id) is None

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Stand gelöscht: Zu löschen' in log.details


# ---------------------------------------------------------------------------
# PUT /stands/reorder
# ---------------------------------------------------------------------------

def test_reorder_stands_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/stands/reorder', json={})
    assert rv.status_code == 422


def test_reorder_stands_applies_new_sort_order(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    a = _make_stand(instance, name='A', sort_order=0)
    b = _make_stand(instance, name='B', sort_order=1)

    rv = c.put(f'/api/admin/{instance.slug}/stands/reorder', json={'order': [b.id, a.id]})
    assert rv.status_code == 200

    _db.session.refresh(a)
    _db.session.refresh(b)
    assert b.sort_order == 0
    assert a.sort_order == 1


def test_reorder_stands_ignores_unknown_ids(client, admin_user, instance):
    """Fremde/nicht existierende IDs in der order-Liste dürfen nicht crashen."""
    c = _admin_client(client, admin_user)
    a = _make_stand(instance, name='A', sort_order=0)

    rv = c.put(f'/api/admin/{instance.slug}/stands/reorder', json={'order': [99999, a.id]})
    assert rv.status_code == 200
    _db.session.refresh(a)
    assert a.sort_order == 1


def test_reorder_stands_cannot_reorder_other_instance_stand(client, admin_user, instance, other_instance):
    """Stand-IDs einer fremden Instanz dürfen nicht (versehentlich) mit-sortiert werden."""
    c = _admin_client(client, admin_user)
    foreign = _make_stand(other_instance, name='Fremd', sort_order=5)

    rv = c.put(f'/api/admin/{instance.slug}/stands/reorder', json={'order': [foreign.id]})
    assert rv.status_code == 200
    _db.session.refresh(foreign)
    assert foreign.sort_order == 5  # unverändert
