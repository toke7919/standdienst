"""Tests für den Volunteer-Bereich: Profil-Update, Optimistic Locking, Passwort-Reset."""
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from app.extensions import db as _db
from app.models import Volunteer


# ---------------------------------------------------------------------------
# Profil-Update
# ---------------------------------------------------------------------------

def test_profile_update_name(client, instance, volunteer, volunteer_token):
    rv = client.put(f'/api/volunteer/{instance.slug}/profile',
                    json={'first_name': 'Neuer', 'last_name': 'Name'})
    assert rv.status_code == 200
    _db.session.refresh(volunteer)
    assert volunteer.name == 'Neuer Name'
    assert volunteer.first_name == 'Neuer'
    assert volunteer.last_name == 'Name'


def test_profile_update_returns_updated_at(client, instance, volunteer, volunteer_token):
    rv = client.put(f'/api/volunteer/{instance.slug}/profile',
                    json={'first_name': 'Mit', 'last_name': 'Timestamp'})
    assert rv.status_code == 200
    assert 'updated_at' in rv.get_json()['data']


def test_profile_update_password_success(client, instance, volunteer, volunteer_token):
    rv = client.put(f'/api/volunteer/{instance.slug}/profile',
                    json={'password': 'NeuesPasswort99!'})
    assert rv.status_code == 200
    _db.session.refresh(volunteer)
    assert volunteer.check_password('NeuesPasswort99!')


def test_profile_update_password_too_short(client, instance, volunteer, volunteer_token):
    rv = client.put(f'/api/volunteer/{instance.slug}/profile',
                    json={'password': 'kurz'})
    assert rv.status_code == 400


def test_profile_update_requires_auth(client, instance):
    rv = client.put(f'/api/volunteer/{instance.slug}/profile',
                    json={'first_name': 'Anonym'})
    assert rv.status_code == 401


# ---------------------------------------------------------------------------
# Optimistic Locking
# ---------------------------------------------------------------------------

def test_profile_update_optimistic_lock_conflict(client, instance, volunteer, volunteer_token):
    """Veraltetes updated_at → 409 Conflict."""
    rv = client.put(f'/api/volunteer/{instance.slug}/profile',
                    json={'first_name': 'Veraltet', 'updated_at': '2020-01-01T00:00:00+00:00'})
    assert rv.status_code == 409


def test_profile_update_no_conflict_without_timestamp(client, instance, volunteer, volunteer_token):
    """Ohne updated_at kein Konflikt (optionaler Mechanismus)."""
    rv = client.put(f'/api/volunteer/{instance.slug}/profile',
                    json={'first_name': 'Kein', 'last_name': 'Lock'})
    assert rv.status_code == 200


# ---------------------------------------------------------------------------
# Volunteer-Passwort-Reset-Flow
# ---------------------------------------------------------------------------

def _setup_reset_token(volunteer):
    raw = secrets.token_urlsafe(32)
    volunteer.reset_token = hashlib.sha256(raw.encode()).hexdigest()
    volunteer.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    _db.session.commit()
    return raw


def test_volunteer_reset_password_success(client, instance, volunteer):
    raw = _setup_reset_token(volunteer)
    rv = client.post(f'/api/public/{instance.slug}/reset-password',
                     json={'token': raw, 'password': 'NeuesPasswort1!'})
    assert rv.status_code == 200

    _db.session.refresh(volunteer)
    assert volunteer.reset_token is None
    assert volunteer.check_password('NeuesPasswort1!')


def test_volunteer_reset_password_too_short(client, instance, volunteer):
    raw = _setup_reset_token(volunteer)
    rv = client.post(f'/api/public/{instance.slug}/reset-password',
                     json={'token': raw, 'password': 'kurz'})
    assert rv.status_code == 400
    _db.session.refresh(volunteer)
    # Token nicht verbraucht
    assert volunteer.reset_token is not None


def test_volunteer_reset_password_invalid_token(client, instance):
    rv = client.post(f'/api/public/{instance.slug}/reset-password',
                     json={'token': 'gefälschter-token', 'password': 'NeuesPasswort1!'})
    assert rv.status_code == 400


def test_volunteer_reset_password_expired_token(client, instance, volunteer):
    raw = secrets.token_urlsafe(32)
    volunteer.reset_token = hashlib.sha256(raw.encode()).hexdigest()
    volunteer.reset_token_expires = datetime.now(timezone.utc) - timedelta(seconds=1)
    _db.session.commit()

    rv = client.post(f'/api/public/{instance.slug}/reset-password',
                     json={'token': raw, 'password': 'NeuesPasswort1!'})
    assert rv.status_code == 400
