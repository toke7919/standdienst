"""Funktionale Tests für app/api/volunteer.py – Schicht-Anmeldung, Essensspenden,
DSGVO-Datenauskunft per E-Mail.

Profil-Update, Passwort-Reset, iCal-Export und grundlegendes Schichten-Listing
sind bereits in test_volunteer_api.py abgedeckt, meine-daten/Selbstlöschung in
test_dsgvo.py. volunteer.py importiert is_mail_configured/send_mail auf
Modulebene -> gemockt wird auf app.api.volunteer.<name>.
"""
from datetime import date, time, datetime, timedelta, timezone
from unittest.mock import patch

from app.extensions import db as _db
from app.models import (
    Stand, EventDate, Shift, Registration, SiteSettings,
    FoodDonationType, FoodDonation, Volunteer, ActivityLog,
)
from tests.conftest import login as _login


def _volunteer_login(client, instance, volunteer):
    rv = client.post('/api/auth/volunteer-login', json={
        'slug': instance.slug, 'email': volunteer.email, 'password': 'TestPass1!',
    })
    assert rv.status_code == 200
    return rv


def _make_shift(instance, stand_name='Stand', day=date(2026, 9, 1),
                start=time(10, 0), end=time(12, 0), max_volunteers=2, is_draft=False):
    stand = Stand(instance_id=instance.id, name=stand_name, sort_order=0)
    _db.session.add(stand)
    _db.session.flush()
    ed = EventDate(instance_id=instance.id, date=day, is_draft=is_draft)
    _db.session.add(ed)
    _db.session.flush()
    shift = Shift(stand_id=stand.id, event_date_id=ed.id,
                  start_time=start, end_time=end, max_volunteers=max_volunteers)
    _db.session.add(shift)
    _db.session.commit()
    return shift


def _site_settings(instance):
    return _db.session.query(SiteSettings).filter_by(instance_id=instance.id).first()


# ---------------------------------------------------------------------------
# GET /shifts
# ---------------------------------------------------------------------------

def test_list_shifts_disabled_returns_403(client, instance, volunteer, volunteer_token):
    _site_settings(instance).shifts_enabled = False
    _db.session.commit()
    rv = client.get(f'/api/volunteer/{instance.slug}/shifts')
    assert rv.status_code == 403


def test_list_shifts_empty_state_when_no_dates_or_stands(client, instance, volunteer, volunteer_token):
    rv = client.get(f'/api/volunteer/{instance.slug}/shifts')
    assert rv.status_code == 200
    assert rv.get_json()['data'] == []


# ---------------------------------------------------------------------------
# GET /shifts/events (SSE)
# ---------------------------------------------------------------------------

def test_shift_events_sse_fallback_without_redis(client, instance, volunteer, volunteer_token):
    rv = client.get(f'/api/volunteer/{instance.slug}/shifts/events')
    assert rv.status_code == 200
    assert rv.mimetype == 'text/event-stream'
    assert b'unavailable' in rv.data


# ---------------------------------------------------------------------------
# POST /shifts/<id>/register
# ---------------------------------------------------------------------------

def test_register_shift_site_locked_returns_403(client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance)
    settings = _site_settings(instance)
    settings.site_locked = True
    settings.lock_message = 'Wartungsarbeiten'
    _db.session.commit()

    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 403
    assert 'Wartungsarbeiten' in rv.get_json()['error']


def test_register_shift_after_deadline_returns_403(client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance)
    settings = _site_settings(instance)
    settings.registration_deadline = datetime.now(timezone.utc) - timedelta(days=1)
    _db.session.commit()

    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 403


def test_register_shift_not_found_returns_404(client, instance, volunteer, volunteer_token):
    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/99999/register')
    assert rv.status_code == 404


def test_register_shift_from_other_instance_returns_404(client, instance, other_instance, volunteer, volunteer_token):
    foreign_shift = _make_shift(other_instance, stand_name='Fremd')
    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{foreign_shift.id}/register')
    assert rv.status_code == 404


def test_register_shift_draft_event_returns_404(client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance, is_draft=True)
    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 404


def test_register_shift_full_returns_409(client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance, max_volunteers=1)
    other_vol = Volunteer(instance_id=instance.id, name='Andere', first_name='Andere')
    _db.session.add(other_vol)
    _db.session.flush()
    _db.session.add(Registration(volunteer_id=other_vol.id, shift_id=shift.id))
    _db.session.commit()

    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 409


def test_register_shift_already_registered_returns_409(client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance)
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 409


def test_register_shift_time_overlap_returns_409(client, instance, volunteer, volunteer_token):
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 5), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    stand = Stand(instance_id=instance.id, name='Stand', sort_order=0)
    _db.session.add(stand)
    _db.session.flush()
    shift1 = Shift(stand_id=stand.id, event_date_id=ed.id, start_time=time(10, 0), end_time=time(12, 0))
    shift2 = Shift(stand_id=stand.id, event_date_id=ed.id, start_time=time(11, 0), end_time=time(13, 0))
    _db.session.add_all([shift1, shift2])
    _db.session.flush()
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift1.id))
    _db.session.commit()

    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift2.id}/register')
    assert rv.status_code == 409


@patch('app.api.volunteer.send_mail')
@patch('app.api.volunteer.is_mail_configured', return_value=True)
def test_register_shift_success_sends_confirmation_mail(mock_configured, mock_send, client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance)
    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 201
    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == volunteer.email

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.SHIFT_REGISTER).first()
    assert log is not None


@patch('app.api.volunteer.is_mail_configured', return_value=True)
def test_register_shift_skips_confirmation_mail_when_disabled(mock_configured, client, instance, volunteer, volunteer_token):
    volunteer.email_confirmation_enabled = False
    _db.session.commit()
    shift = _make_shift(instance)
    with patch('app.api.volunteer.send_mail') as mock_send:
        rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
        assert rv.status_code == 201
        mock_send.assert_not_called()


@patch('app.api.volunteer.send_mail')
@patch('app.api.volunteer.is_mail_configured', return_value=True)
def test_register_shift_uses_instance_primary_color(mock_configured, mock_send, client, instance, volunteer, volunteer_token):
    _site_settings(instance).primary_color = '#123456'
    _db.session.commit()
    shift = _make_shift(instance)
    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 201
    mock_send.assert_called_once()


@patch('app.api.volunteer.send_mail', side_effect=RuntimeError('SMTP down'))
@patch('app.api.volunteer.is_mail_configured', return_value=True)
def test_register_shift_still_succeeds_when_confirmation_mail_fails(mock_configured, mock_send, client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance)
    rv = client.post(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 201


def test_send_shift_confirmation_falls_back_to_loading_stand_name(client, instance, volunteer, volunteer_token):
    """Ohne übergebenen stand_name (z.B. bei künftigen Aufrufern) muss der Stand nachgeladen werden."""
    from app.api.volunteer import _send_shift_confirmation
    shift = _make_shift(instance)
    with patch('app.api.volunteer.is_mail_configured', return_value=True), \
         patch('app.api.volunteer.send_mail') as mock_send:
        _send_shift_confirmation(volunteer, shift, instance, _site_settings(instance), stand_name=None)
    mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# DELETE /shifts/<id>/register
# ---------------------------------------------------------------------------

def test_unregister_shift_not_registered_returns_404(client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance)
    rv = client.delete(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 404


def test_unregister_shift_after_deadline_returns_403(client, instance, volunteer, volunteer_token):
    tomorrow = date.today() + timedelta(days=1)
    shift = _make_shift(instance, day=tomorrow, start=time(0, 30), end=time(2, 0))
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    settings = _site_settings(instance)
    settings.unregister_deadline_hours = 48  # Schicht beginnt in < 48h -> Abmeldeschluss überschritten
    _db.session.commit()

    rv = client.delete(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 403


def test_unregister_shift_success(client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance)
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    rv = client.delete(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 204
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.SHIFT_UNREGISTER).first()
    assert log is not None


def test_unregister_shift_success_within_deadline(client, instance, volunteer, volunteer_token):
    """unregister_deadline_hours gesetzt, aber Schicht liegt weit genug in der Zukunft."""
    far_future = date.today() + timedelta(days=30)
    shift = _make_shift(instance, day=far_future)
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _site_settings(instance).unregister_deadline_hours = 24
    _db.session.commit()

    rv = client.delete(f'/api/volunteer/{instance.slug}/shifts/{shift.id}/register')
    assert rv.status_code == 204


# ---------------------------------------------------------------------------
# GET /my-registrations
# ---------------------------------------------------------------------------

def test_my_registrations_lists_own_registrations(client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance)
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    rv = client.get(f'/api/volunteer/{instance.slug}/my-registrations')
    assert rv.status_code == 200
    assert len(rv.get_json()['data']) == 1


# ---------------------------------------------------------------------------
# PUT /profile – Zusatzfälle (Name/Toggles), DELETE /profile – Log-Details
# ---------------------------------------------------------------------------

def test_update_profile_empty_first_name_rejected(client, instance, volunteer, volunteer_token):
    rv = client.put(f'/api/volunteer/{instance.slug}/profile', json={'first_name': '   '})
    assert rv.status_code == 422


def test_update_profile_toggles_notifications_and_email_confirmation(client, instance, volunteer, volunteer_token):
    rv = client.put(f'/api/volunteer/{instance.slug}/profile', json={
        'notifications_enabled': True, 'email_confirmation_enabled': False,
    })
    assert rv.status_code == 200
    _db.session.refresh(volunteer)
    assert volunteer.notifications_enabled is True
    assert volunteer.email_confirmation_enabled is False


def test_self_soft_delete_activity_log_mentions_registration_and_donation_count(client, instance, volunteer, volunteer_token):
    shift = _make_shift(instance)
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    rv = client.delete(f'/api/volunteer/{instance.slug}/profile', json={'password': 'TestPass1!'})
    assert rv.status_code == 204
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.VOLUNTEER_DELETE).first()
    assert '1 Dienst-Anm.' in log.details


# ---------------------------------------------------------------------------
# GET /food-types
# ---------------------------------------------------------------------------

def test_list_food_types_disabled_returns_403(client, instance, volunteer, volunteer_token):
    _site_settings(instance).food_donations_enabled = False
    _db.session.commit()
    rv = client.get(f'/api/volunteer/{instance.slug}/food-types')
    assert rv.status_code == 403


def test_list_food_types_excludes_draft_event_dates(client, instance, volunteer, volunteer_token):
    ed_pub = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    ed_draft = EventDate(instance_id=instance.id, date=date(2026, 9, 2), is_draft=True)
    _db.session.add_all([ed_pub, ed_draft])
    _db.session.flush()
    _db.session.add_all([
        FoodDonationType(instance_id=instance.id, event_date_id=ed_pub.id, name='Sichtbar'),
        FoodDonationType(instance_id=instance.id, event_date_id=ed_draft.id, name='Versteckt'),
    ])
    _db.session.commit()

    rv = client.get(f'/api/volunteer/{instance.slug}/food-types')
    assert rv.status_code == 200
    names = [t['name'] for t in rv.get_json()['data']]
    assert names == ['Sichtbar']


# ---------------------------------------------------------------------------
# GET /food-donations
# ---------------------------------------------------------------------------

def test_list_food_donations_disabled_returns_403(client, instance, volunteer, volunteer_token):
    _site_settings(instance).food_donations_enabled = False
    _db.session.commit()
    rv = client.get(f'/api/volunteer/{instance.slug}/food-donations')
    assert rv.status_code == 403


def test_list_food_donations_shows_mine_guest_and_excludes_deleted_volunteer(client, instance, volunteer, volunteer_token):
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    ft = FoodDonationType(instance_id=instance.id, event_date_id=ed.id, name='Kuchen')
    _db.session.add(ft)
    _db.session.flush()

    other_vol = Volunteer(instance_id=instance.id, name='Andere', first_name='Andere')
    _db.session.add(other_vol)
    _db.session.flush()

    _db.session.add_all([
        FoodDonation(volunteer_id=volunteer.id, food_type_id=ft.id, description='Apfelkuchen'),
        FoodDonation(guest_name='Gast', food_type_id=ft.id, description='Käsekuchen'),
        FoodDonation(volunteer_id=other_vol.id, food_type_id=ft.id, description='Nusskuchen'),
    ])
    _db.session.commit()
    other_vol.soft_delete()
    _db.session.commit()

    rv = client.get(f'/api/volunteer/{instance.slug}/food-donations')
    assert rv.status_code == 200
    donations = rv.get_json()['data'][0]['donations']
    descriptions = {d['description'] for d in donations}
    assert descriptions == {'Apfelkuchen', 'Käsekuchen'}  # Nusskuchen (gelöschter Volunteer) fehlt
    mine = {d['description']: d['is_mine'] for d in donations}
    assert mine['Apfelkuchen'] is True
    assert mine['Käsekuchen'] is False


# ---------------------------------------------------------------------------
# POST /food-donations
# ---------------------------------------------------------------------------

def test_create_food_donation_after_deadline_returns_403(client, instance, volunteer, volunteer_token):
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    ft = FoodDonationType(instance_id=instance.id, event_date_id=ed.id, name='Kuchen')
    _db.session.add(ft)
    settings = _site_settings(instance)
    settings.registration_deadline = datetime.now(timezone.utc) - timedelta(days=1)
    _db.session.commit()

    rv = client.post(f'/api/volunteer/{instance.slug}/food-donations',
                     json={'food_type_id': ft.id, 'description': 'Kuchen'})
    assert rv.status_code == 403


def test_create_food_donation_validation_error(client, instance, volunteer, volunteer_token):
    rv = client.post(f'/api/volunteer/{instance.slug}/food-donations', json={})
    assert rv.status_code == 422


def test_create_food_donation_type_not_found(client, instance, volunteer, volunteer_token):
    rv = client.post(f'/api/volunteer/{instance.slug}/food-donations',
                     json={'food_type_id': 99999, 'description': 'Kuchen'})
    assert rv.status_code == 404


def test_create_food_donation_success(client, instance, volunteer, volunteer_token):
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    ft = FoodDonationType(instance_id=instance.id, event_date_id=ed.id, name='Kuchen')
    _db.session.add(ft)
    _db.session.commit()

    rv = client.post(f'/api/volunteer/{instance.slug}/food-donations',
                     json={'food_type_id': ft.id, 'description': 'Apfelkuchen'})
    assert rv.status_code == 201
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.FOOD_REGISTER).first()
    assert log is not None


# ---------------------------------------------------------------------------
# DELETE /food-donations/<id>
# ---------------------------------------------------------------------------

def test_delete_food_donation_not_found(client, instance, volunteer, volunteer_token):
    rv = client.delete(f'/api/volunteer/{instance.slug}/food-donations/99999')
    assert rv.status_code == 404


def test_delete_food_donation_of_other_volunteer_returns_404(client, instance, volunteer, volunteer_token):
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    ft = FoodDonationType(instance_id=instance.id, event_date_id=ed.id, name='Kuchen')
    _db.session.add(ft)
    _db.session.flush()
    other_vol = Volunteer(instance_id=instance.id, name='Andere', first_name='Andere')
    _db.session.add(other_vol)
    _db.session.flush()
    donation = FoodDonation(volunteer_id=other_vol.id, food_type_id=ft.id, description='Fremd')
    _db.session.add(donation)
    _db.session.commit()

    rv = client.delete(f'/api/volunteer/{instance.slug}/food-donations/{donation.id}')
    assert rv.status_code == 404


def test_delete_food_donation_success(client, instance, volunteer, volunteer_token):
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    ft = FoodDonationType(instance_id=instance.id, event_date_id=ed.id, name='Kuchen')
    _db.session.add(ft)
    _db.session.flush()
    donation = FoodDonation(volunteer_id=volunteer.id, food_type_id=ft.id, description='Meine Spende')
    _db.session.add(donation)
    _db.session.commit()
    donation_id = donation.id

    rv = client.delete(f'/api/volunteer/{instance.slug}/food-donations/{donation_id}')
    assert rv.status_code == 204
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.FOOD_UNREGISTER).first()
    assert log is not None
    assert 'Meine Spende' in log.details


# ---------------------------------------------------------------------------
# POST /meine-daten/export – DSGVO Art. 15 per E-Mail
# ---------------------------------------------------------------------------

def test_meine_daten_export_no_email_returns_400(client, instance):
    """Anonym registrierte Volunteers (keine E-Mail) loggen sich direkt bei der
    Registrierung ein (siehe test_registration.py) -> darüber den Fall nachbauen."""
    from tests.test_registration import _altcha_solution
    answer = _altcha_solution(client, instance.slug)
    rv = client.post(f'/api/public/{instance.slug}/register', json={
        'first_name': 'Anonym', 'last_name': 'Tester', 'altcha': answer,
    })
    assert rv.status_code == 201

    rv = client.post(f'/api/volunteer/{instance.slug}/meine-daten/export')
    assert rv.status_code == 400


@patch('app.api.volunteer.is_mail_configured', return_value=False)
def test_meine_daten_export_mail_not_configured_returns_503(mock_mail, client, instance, volunteer, volunteer_token):
    rv = client.post(f'/api/volunteer/{instance.slug}/meine-daten/export')
    assert rv.status_code == 503


@patch('app.api.volunteer.send_mail')
@patch('app.api.volunteer.is_mail_configured', return_value=True)
def test_meine_daten_export_success(mock_configured, mock_send, client, instance, volunteer, volunteer_token):
    rv = client.post(f'/api/volunteer/{instance.slug}/meine-daten/export')
    assert rv.status_code == 200
    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == volunteer.email


@patch('app.api.volunteer.send_mail')
@patch('app.api.volunteer.is_mail_configured', return_value=True)
def test_meine_daten_export_uses_instance_primary_color(mock_configured, mock_send, client, instance, volunteer, volunteer_token):
    _site_settings(instance).primary_color = '#654321'
    _db.session.commit()
    rv = client.post(f'/api/volunteer/{instance.slug}/meine-daten/export')
    assert rv.status_code == 200
    mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# GET /my-registrations/ical – mit tatsächlichen Terminen
# ---------------------------------------------------------------------------

def test_my_registrations_ical_contains_registered_shift(client, instance, volunteer, volunteer_token):
    """test_volunteer_api.py::test_ical_export_responds_ok prüft nur den Leerzustand
    (keine Registrierung) -> die Event-Schleife wird dort nie durchlaufen."""
    shift = _make_shift(instance, stand_name='Kasse')
    _db.session.add(Registration(volunteer_id=volunteer.id, shift_id=shift.id))
    _db.session.commit()

    rv = client.get(f'/api/volunteer/{instance.slug}/my-registrations/ical')
    assert rv.status_code == 200
    assert b'Kasse' in rv.data
    assert b'BEGIN:VEVENT' in rv.data
