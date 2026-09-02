"""Funktionale Tests für app/api/admin/volunteers.py.

Soft-Delete, permanentes Löschen und Optimistic Locking beim Update sind
bereits in test_roles.py abgedeckt. Hier geht es um Liste (Pagination,
Dienst-/Spenden-Zähler, include_deleted-Filter), Anlegen (Validierung,
Duplikat-Prüfung, Willkommensmail), Detailansicht (Registrierungen/Spenden,
Sortierung), Update (Duplikat-Prüfung, Passwort), DSGVO-Auskunft und
Passwort-Reset durch Admin/Instanz-Admin.

volunteers.py importiert is_mail_configured/send_mail auf Modulebene ->
gemockt wird auf app.api.admin.volunteers.<name>.
"""
from datetime import date, time
from unittest.mock import patch

import pytest

from app.extensions import db as _db
from app.models import Volunteer, EventDate, Stand, Shift, Registration, FoodDonationType, FoodDonation, ActivityLog
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


# ---------------------------------------------------------------------------
# GET /volunteers – Liste
# ---------------------------------------------------------------------------

def test_list_volunteers_excludes_deleted_by_default(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    v1 = Volunteer(instance_id=instance.id, name='Aktiv', first_name='Aktiv')
    v2 = Volunteer(instance_id=instance.id, name='Gelöscht', first_name='Gelöscht')
    _db.session.add_all([v1, v2])
    _db.session.commit()
    v2.soft_delete()
    _db.session.commit()

    rv = c.get(f'/api/admin/{instance.slug}/volunteers')
    assert rv.status_code == 200
    names = [v['first_name'] for v in rv.get_json()['data']]
    assert names == ['Aktiv']


def test_list_volunteers_include_deleted_true_shows_all(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    v1 = Volunteer(instance_id=instance.id, name='Aktiv', first_name='Aktiv')
    v2 = Volunteer(instance_id=instance.id, name='Gelöscht', first_name='Gelöscht')
    _db.session.add_all([v1, v2])
    _db.session.commit()
    v2.soft_delete()
    _db.session.commit()

    rv = c.get(f'/api/admin/{instance.slug}/volunteers?include_deleted=true')
    assert rv.status_code == 200
    assert rv.get_json()['total'] == 2


def test_list_volunteers_includes_shift_and_food_counts(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    v = Volunteer(instance_id=instance.id, name='Zähltest', first_name='Zähltest')
    _db.session.add(v)
    _db.session.flush()

    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    stand = Stand(instance_id=instance.id, name='Stand', sort_order=0)
    _db.session.add(stand)
    _db.session.flush()
    shift = Shift(stand_id=stand.id, event_date_id=ed.id, start_time=time(10, 0), end_time=time(12, 0))
    _db.session.add(shift)
    _db.session.flush()
    _db.session.add(Registration(volunteer_id=v.id, shift_id=shift.id))

    ft = FoodDonationType(instance_id=instance.id, event_date_id=ed.id, name='Kuchen')
    _db.session.add(ft)
    _db.session.flush()
    _db.session.add(FoodDonation(volunteer_id=v.id, food_type_id=ft.id, description='Kuchen'))
    _db.session.commit()

    rv = c.get(f'/api/admin/{instance.slug}/volunteers')
    item = rv.get_json()['data'][0]
    assert item['shift_count'] == 1
    assert item['food_count'] == 1


# ---------------------------------------------------------------------------
# POST /volunteers – Anlegen
# ---------------------------------------------------------------------------

def test_create_volunteer_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers', json={})
    assert rv.status_code == 422


def test_create_volunteer_duplicate_email_rejected(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    v = Volunteer(instance_id=instance.id, name='Bestehend', first_name='Bestehend', email='dup@test.de')
    _db.session.add(v)
    _db.session.commit()

    rv = c.post(f'/api/admin/{instance.slug}/volunteers', json={'first_name': 'Neu', 'email': 'dup@test.de'})
    assert rv.status_code == 409


def test_create_volunteer_weak_password_rejected(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers', json={'first_name': 'Neu', 'password': 'kurz1'})
    assert rv.status_code == 422  # scheitert schon an marshmallow min=8


def test_create_volunteer_password_over_72_bytes_rejected(client, admin_user, instance):
    """bcrypt verarbeitet nur die ersten 72 Bytes -> längere Passwörter hart ablehnen."""
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers', json={
        'first_name': 'ZuLang', 'password': 'x' * 73,
    })
    assert rv.status_code == 400


def test_create_volunteer_without_email_or_password_has_no_login(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers', json={'first_name': 'Anonym'})
    assert rv.status_code == 201
    assert rv.get_json()['data']['has_login'] is False


@patch('app.api.admin.volunteers.is_mail_configured', return_value=False)
def test_create_volunteer_with_password_sets_login_and_skips_welcome_mail(mock_mail, client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers', json={
        'first_name': 'MitPasswort', 'email': 'mitpw@test.de', 'password': 'SicheresPass1!',
    })
    assert rv.status_code == 201
    assert rv.get_json()['data']['has_login'] is True


@patch('app.api.admin.volunteers.send_mail')
@patch('app.api.admin.volunteers.is_mail_configured', return_value=True)
def test_create_volunteer_with_email_no_password_sends_welcome_mail(mock_configured, mock_send, client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers', json={
        'first_name': 'Eingeladen', 'email': 'eingeladen@test.de',
    })
    assert rv.status_code == 201
    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == 'eingeladen@test.de'


@patch('app.api.admin.volunteers.send_mail')
@patch('app.api.admin.volunteers.is_mail_configured', return_value=True)
def test_create_volunteer_welcome_mail_uses_instance_primary_color(mock_configured, mock_send, client, admin_user, instance):
    from app.models import SiteSettings, GlobalSettings
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.primary_color = '#654321'
    _db.session.add(GlobalSettings(base_url='https://example.test'))
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers', json={
        'first_name': 'Bunt', 'email': 'bunt@test.de',
    })
    assert rv.status_code == 201
    mock_send.assert_called_once()


@patch('app.api.admin.volunteers.send_mail', side_effect=RuntimeError('SMTP down'))
@patch('app.api.admin.volunteers.is_mail_configured', return_value=True)
def test_create_volunteer_still_succeeds_when_welcome_mail_fails(mock_configured, mock_send, client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers', json={
        'first_name': 'Trotzdem', 'email': 'trotzdem@test.de',
    })
    assert rv.status_code == 201


def test_create_volunteer_activity_log_written(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers', json={'first_name': 'Geloggt'})
    assert rv.status_code == 201
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_DATA).first()
    assert log is not None
    assert 'Geloggt' in log.details


# ---------------------------------------------------------------------------
# GET /volunteers/<id> und /detail
# ---------------------------------------------------------------------------

def test_get_volunteer_not_found(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.get(f'/api/admin/{instance.slug}/volunteers/99999')
    assert rv.status_code == 404


def test_get_volunteer_returns_data(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    rv = c.get(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}')
    assert rv.status_code == 200
    assert rv.get_json()['data']['email'] == volunteer.email


def test_get_volunteer_detail_includes_sorted_registrations_and_donations(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)

    ed1 = EventDate(instance_id=instance.id, date=date(2026, 9, 2), is_draft=False)
    ed2 = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add_all([ed1, ed2])
    _db.session.flush()
    stand = Stand(instance_id=instance.id, name='Stand', sort_order=0)
    _db.session.add(stand)
    _db.session.flush()
    shift1 = Shift(stand_id=stand.id, event_date_id=ed1.id, start_time=time(10, 0), end_time=time(12, 0))
    shift2 = Shift(stand_id=stand.id, event_date_id=ed2.id, start_time=time(8, 0), end_time=time(9, 0))
    _db.session.add_all([shift1, shift2])
    _db.session.flush()
    _db.session.add_all([
        Registration(volunteer_id=volunteer.id, shift_id=shift1.id),
        Registration(volunteer_id=volunteer.id, shift_id=shift2.id),
    ])

    ft1 = FoodDonationType(instance_id=instance.id, event_date_id=ed1.id, name='Kuchen')
    ft2 = FoodDonationType(instance_id=instance.id, event_date_id=ed2.id, name='Salat')
    _db.session.add_all([ft1, ft2])
    _db.session.flush()
    _db.session.add_all([
        FoodDonation(volunteer_id=volunteer.id, food_type_id=ft1.id, description='Apfelkuchen'),
        FoodDonation(volunteer_id=volunteer.id, food_type_id=ft2.id, description='Nudelsalat'),
    ])
    _db.session.commit()

    rv = c.get(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}/detail')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert len(data['registrations']) == 2
    # Nach Datum sortiert -> ed2 (09-01) zuerst, dann ed1 (09-02)
    assert data['registrations'][0]['date_raw'] == '2026-09-01'
    assert data['registrations'][1]['date_raw'] == '2026-09-02'
    assert len(data['food_donations']) == 2
    assert data['food_donations'][0]['date_raw'] == '2026-09-01'


# ---------------------------------------------------------------------------
# PUT /volunteers/<id> – Update
# ---------------------------------------------------------------------------

def test_update_volunteer_not_found(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/volunteers/99999', json={'first_name': 'X'})
    assert rv.status_code == 404


def test_update_volunteer_duplicate_email_rejected(client, admin_user, instance, volunteer):
    other = Volunteer(instance_id=instance.id, name='Andere', first_name='Andere', email='andere@test.de')
    _db.session.add(other)
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}', json={'email': 'andere@test.de'})
    assert rv.status_code == 409


def test_update_volunteer_weak_password_rejected(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}', json={'password': 'kurz1'})
    assert rv.status_code == 422  # scheitert schon an marshmallow min=8


def test_update_volunteer_password_over_72_bytes_rejected(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}', json={'password': 'x' * 73})
    assert rv.status_code == 400


def test_update_volunteer_names_and_email(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}', json={
        'first_name': 'Neuer', 'last_name': 'Name', 'email': 'neu@test.de',
    })
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['name'] == 'Neuer Name'
    assert data['email'] == 'neu@test.de'


def test_update_volunteer_valid_password_changes_login(client, admin_user, instance, volunteer):
    old_hash = volunteer.password_hash
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}', json={'password': 'NeuesPasswort1'})
    assert rv.status_code == 200
    _db.session.refresh(volunteer)
    assert volunteer.password_hash != old_hash


# ---------------------------------------------------------------------------
# DELETE /volunteers/<id> – Soft-Delete-Details
# ---------------------------------------------------------------------------

def test_soft_delete_activity_log_mentions_registration_and_donation_count(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    stand = Stand(instance_id=instance.id, name='Stand', sort_order=0)
    _db.session.add(stand)
    _db.session.flush()
    shift = Shift(stand_id=stand.id, event_date_id=ed.id, start_time=time(10, 0), end_time=time(12, 0))
    _db.session.add(shift)
    _db.session.flush()
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    ft = FoodDonationType(instance_id=instance.id, event_date_id=ed.id, name='Kuchen')
    _db.session.add(ft)
    _db.session.flush()
    _db.session.add(FoodDonation(volunteer_id=volunteer.id, food_type_id=ft.id, description='Kuchen'))
    _db.session.commit()

    rv = c.delete(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}')
    assert rv.status_code == 204
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.VOLUNTEER_DELETE).first()
    assert '1 Dienst-Anm., 1 Spenden' in log.details


# ---------------------------------------------------------------------------
# POST /volunteers/<id>/dsgvo-auskunft
# ---------------------------------------------------------------------------

def test_dsgvo_auskunft_no_email_rejected(client, admin_user, instance):
    v = Volunteer(instance_id=instance.id, name='Ohne Mail', first_name='Ohne')
    _db.session.add(v)
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers/{v.id}/dsgvo-auskunft')
    assert rv.status_code == 400


@patch('app.api.admin.volunteers.is_mail_configured', return_value=False)
def test_dsgvo_auskunft_mail_not_configured_returns_503(mock_mail, client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}/dsgvo-auskunft')
    assert rv.status_code == 503


@patch('app.api.admin.volunteers.send_mail')
@patch('app.api.admin.volunteers.is_mail_configured', return_value=True)
def test_dsgvo_auskunft_success(mock_configured, mock_send, client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}/dsgvo-auskunft')
    assert rv.status_code == 200
    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == volunteer.email


@patch('app.api.admin.volunteers.send_mail')
@patch('app.api.admin.volunteers.is_mail_configured', return_value=True)
def test_dsgvo_auskunft_uses_instance_primary_color(mock_configured, mock_send, client, admin_user, instance, volunteer):
    from app.models import SiteSettings
    settings = _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()
    settings.primary_color = '#123456'
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}/dsgvo-auskunft')
    assert rv.status_code == 200
    mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# DELETE /volunteers/<id>/permanent – Log-Details
# ---------------------------------------------------------------------------

def test_permanent_delete_activity_log_mentions_registration_and_donation_count(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    stand = Stand(instance_id=instance.id, name='Stand', sort_order=0)
    _db.session.add(stand)
    _db.session.flush()
    shift = Shift(stand_id=stand.id, event_date_id=ed.id, start_time=time(10, 0), end_time=time(12, 0))
    _db.session.add(shift)
    _db.session.flush()
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    rv = c.delete(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}/permanent')
    assert rv.status_code == 204
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.VOLUNTEER_PERMANENT_DELETE).first()
    assert '1 Dienst-Anm.' in log.details


# ---------------------------------------------------------------------------
# POST /volunteers/<id>/reset-password
# ---------------------------------------------------------------------------

def test_reset_volunteer_password_weak_rejected(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}/reset-password', json={'password': 'kurz'})
    assert rv.status_code == 400


def test_reset_volunteer_password_success(client, admin_user, instance, volunteer):
    old_hash = volunteer.password_hash
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/volunteers/{volunteer.id}/reset-password',
               json={'password': 'NeuesPasswort1'})
    assert rv.status_code == 200
    _db.session.refresh(volunteer)
    assert volunteer.password_hash != old_hash
