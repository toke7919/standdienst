"""Funktionale Tests für app/api/admin/dates.py – Anlegen/Ändern/Löschen.

Autorisierung ist bereits in test_authz_dates.py abgedeckt, has_shifts/
has_food_types-Filter und die Duplicate-Logik bereits in test_admin_dates.py.
Hier nur die noch fehlenden Basis-CRUD-Fälle für POST/PUT/DELETE.
"""
from datetime import date, datetime, timezone, timedelta

from app.extensions import db as _db
from app.models import EventDate, ActivityLog
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


def _make_date(instance, day=date(2026, 9, 1)):
    ed = EventDate(instance_id=instance.id, date=day, is_draft=False)
    _db.session.add(ed)
    _db.session.commit()
    return ed


# ---------------------------------------------------------------------------
# POST /dates
# ---------------------------------------------------------------------------

def test_create_date_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/dates', json={})
    assert rv.status_code == 422


def test_create_date_duplicate_returns_409(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    _make_date(instance, date(2026, 9, 1))
    rv = c.post(f'/api/admin/{instance.slug}/dates', json={'date': '2026-09-01'})
    assert rv.status_code == 409


def test_create_date_success_logs_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/dates', json={'date': '2026-09-01', 'label': 'Herbstfest'})
    assert rv.status_code == 201
    data = rv.get_json()['data']
    assert data['label'] == 'Herbstfest'

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Termin angelegt' in log.details


# ---------------------------------------------------------------------------
# PUT /dates/<id>
# ---------------------------------------------------------------------------

def test_update_date_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/dates/99999', json={'label': 'X'})
    assert rv.status_code == 404


def test_update_date_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ed = _make_date(instance)
    rv = c.put(f'/api/admin/{instance.slug}/dates/{ed.id}', json={'date': 'keine-datumsangabe'})
    assert rv.status_code == 422


def test_update_date_optimistic_lock_conflict(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ed = _make_date(instance)
    stale = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rv = c.put(f'/api/admin/{instance.slug}/dates/{ed.id}', json={
        'label': 'Neu', 'updated_at': stale,
    })
    assert rv.status_code == 409


def test_update_date_success_logs_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ed = _make_date(instance)
    rv = c.put(f'/api/admin/{instance.slug}/dates/{ed.id}', json={'label': 'Umbenannt', 'is_draft': True})
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['label'] == 'Umbenannt'
    assert data['is_draft'] is True

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Termin geändert' in log.details


# ---------------------------------------------------------------------------
# DELETE /dates/<id>
# ---------------------------------------------------------------------------

def test_delete_date_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.delete(f'/api/admin/{instance.slug}/dates/99999')
    assert rv.status_code == 404


def test_delete_date_success_logs_activity(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    ed = _make_date(instance)
    ed_id = ed.id
    rv = c.delete(f'/api/admin/{instance.slug}/dates/{ed_id}')
    assert rv.status_code == 204
    assert _db.session.get(EventDate, ed_id) is None

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Termin gelöscht' in log.details


# ---------------------------------------------------------------------------
# POST /dates/<id>/duplicate – Zusatzfall: Quelltermin nicht gefunden
# ---------------------------------------------------------------------------

def test_duplicate_date_source_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/dates/99999/duplicate', json={'date': '2026-09-01'})
    assert rv.status_code == 404
