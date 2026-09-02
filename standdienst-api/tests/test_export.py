"""Funktionale Tests für app/api/admin/export.py.

Autorisierung (@require_staff, Instanz-Zugriffsschutz) ist bereits in
test_authz_export_import.py abgedeckt. Hier geht es um Statuscode, Response-Form
und Inhalt der einzelnen Export-Formate (CSV, ODS, PDF, iCal) sowie Edge-Cases
(leerer Datenbestand, Gast-Registrierungen, HTML-Escaping, E-Mail-Versand).
"""
import csv
import io
from datetime import date, datetime, time, timezone
from unittest.mock import patch

import pytest
from icalendar import Calendar
from odf.opendocument import load as load_ods
from odf.table import Table
from odf.text import P

from app.api.admin.export import _pdf_branding
from app.extensions import db as _db
from app.models import EventDate, Stand, Shift, Registration, Volunteer, FoodDonationType, FoodDonation, SiteSettings
from tests.conftest import login as _login


@pytest.fixture
def export_client(client, admin_user):
    _login(client, admin_user.email)
    return client


@pytest.fixture
def export_setup(instance, volunteer):
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 1), label='Herbstfest', is_draft=False)
    _db.session.add(ed)
    _db.session.flush()

    stand = Stand(instance_id=instance.id, name='Grillstand', sort_order=0)
    _db.session.add(stand)
    _db.session.flush()

    shift = Shift(stand_id=stand.id, event_date_id=ed.id,
                  start_time=time(10, 0), end_time=time(14, 0), max_volunteers=2)
    _db.session.add(shift)
    _db.session.flush()

    reg_vol = Registration(volunteer_id=volunteer.id, shift_id=shift.id)
    reg_guest = Registration(guest_name='Gast <b>Meier</b>', shift_id=shift.id)
    _db.session.add_all([reg_vol, reg_guest])

    ft = FoodDonationType(
        instance_id=instance.id, event_date_id=ed.id, name='Kuchen',
        refrigeration_enabled=True,
        delivery_datetime=datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
        delivery_location='Küche',
    )
    _db.session.add(ft)
    _db.session.flush()

    don_vol = FoodDonation(volunteer_id=volunteer.id, food_type_id=ft.id,
                           description='Apfelkuchen', needs_refrigeration=False)
    don_guest = FoodDonation(guest_name='Gast Spender', food_type_id=ft.id,
                             description='Käsekuchen', needs_refrigeration=True)
    _db.session.add_all([don_vol, don_guest])
    _db.session.commit()

    return {
        'instance': instance, 'event_date': ed, 'stand': stand, 'shift': shift,
        'volunteer': volunteer, 'food_type': ft,
    }


def _read_csv(rv):
    return list(csv.reader(io.StringIO(rv.data.decode('utf-8-sig')), delimiter=';'))


# ---------------------------------------------------------------------------
# CSV – Anmeldungen
# ---------------------------------------------------------------------------

def test_export_csv_registrations_contains_rows(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.get(f'/api/admin/{instance.slug}/export/csv/registrations')
    assert rv.status_code == 200
    assert rv.mimetype == 'text/csv'
    rows = _read_csv(rv)
    assert rows[0] == ['Stand', 'Datum', 'Uhrzeit', 'Helfer', 'E-Mail', 'Angemeldet am']
    names = {r[3] for r in rows[1:]}
    assert export_setup['volunteer'].name in names
    assert 'Gast &lt;b&gt;Meier&lt;/b&gt;' in names  # HTML-escaped, kein echtes Markup


def test_export_csv_registrations_empty_state_only_header(export_client, instance):
    rv = export_client.get(f'/api/admin/{instance.slug}/export/csv/registrations')
    assert rv.status_code == 200
    assert len(_read_csv(rv)) == 1


def test_export_csv_volunteers_excludes_soft_deleted(export_client, instance):
    v1 = Volunteer(instance_id=instance.id, name='Aktiv Helfer', email='aktiv@test.de')
    v1.set_password('TestPass1!')
    v2 = Volunteer(instance_id=instance.id, name='Wird Geloescht', email='geloescht@test.de')
    v2.set_password('TestPass1!')
    _db.session.add_all([v1, v2])
    _db.session.commit()
    v2.soft_delete()
    _db.session.commit()

    rv = export_client.get(f'/api/admin/{instance.slug}/export/csv/volunteers')
    assert rv.status_code == 200
    names = [r[0] for r in _read_csv(rv)[1:]]
    assert names == ['Aktiv Helfer']


def test_export_csv_volunteers_shift_count(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.get(f'/api/admin/{instance.slug}/export/csv/volunteers')
    rows = {r[0]: r for r in _read_csv(rv)[1:]}
    assert rows[export_setup['volunteer'].name][3] == '1'


# ---------------------------------------------------------------------------
# ODS – Dienste / Essen / Legacy
# ---------------------------------------------------------------------------

def _ods_all_text(rv):
    doc = load_ods(io.BytesIO(rv.data))
    texts = []
    for elem in doc.spreadsheet.getElementsByType(P):
        texts.append(str(elem))
    return texts


def test_export_ods_dienste_contains_stand_and_helper(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.get(f'/api/admin/{instance.slug}/export/ods/dienste')
    assert rv.status_code == 200
    assert rv.mimetype == 'application/vnd.oasis.opendocument.spreadsheet'
    texts = _ods_all_text(rv)
    assert any('Grillstand' in t for t in texts)
    assert any(export_setup['volunteer'].name in t for t in texts)


def test_export_ods_dienste_empty_state_has_placeholder_sheet(export_client, instance):
    rv = export_client.get(f'/api/admin/{instance.slug}/export/ods/dienste')
    assert rv.status_code == 200
    doc = load_ods(io.BytesIO(rv.data))
    names = [t.getAttribute('name') for t in doc.spreadsheet.getElementsByType(Table)]
    assert names == ['Dienste']


def test_export_ods_essen_contains_donation(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.get(f'/api/admin/{instance.slug}/export/ods/essen')
    assert rv.status_code == 200
    texts = _ods_all_text(rv)
    assert any('Apfelkuchen' in t for t in texts)
    assert any('Ja' == t for t in texts)  # Kühlpflichtig-Spalte für Gast-Spende


def test_export_ods_essen_empty_state_has_placeholder_sheet(export_client, instance):
    rv = export_client.get(f'/api/admin/{instance.slug}/export/ods/essen')
    assert rv.status_code == 200
    doc = load_ods(io.BytesIO(rv.data))
    names = [t.getAttribute('name') for t in doc.spreadsheet.getElementsByType(Table)]
    assert names == ['Essensspenden']


def test_export_ods_essen_food_type_without_donations_shows_placeholder(export_client, instance):
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 2), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    ft = FoodDonationType(instance_id=instance.id, event_date_id=ed.id, name='Salate',
                          refrigeration_enabled=False)
    _db.session.add(ft)
    _db.session.commit()

    rv = export_client.get(f'/api/admin/{instance.slug}/export/ods/essen')
    assert rv.status_code == 200
    texts = _ods_all_text(rv)
    assert '—' in texts


def test_export_ods_legacy_contains_registration(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.get(f'/api/admin/{instance.slug}/export/ods')
    assert rv.status_code == 200
    texts = _ods_all_text(rv)
    assert any(export_setup['volunteer'].name in t for t in texts)


# ---------------------------------------------------------------------------
# PDF – Dienste / Essen / Legacy (GET)
# ---------------------------------------------------------------------------

def test_export_pdf_dienste_returns_valid_pdf(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.get(f'/api/admin/{instance.slug}/export/pdf/dienste')
    assert rv.status_code == 200
    assert rv.mimetype == 'application/pdf'
    assert rv.data.startswith(b'%PDF')


def test_export_pdf_essen_returns_valid_pdf(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.get(f'/api/admin/{instance.slug}/export/pdf/essen')
    assert rv.status_code == 200
    assert rv.data.startswith(b'%PDF')


def test_export_pdf_legacy_returns_valid_pdf(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.get(f'/api/admin/{instance.slug}/export/pdf')
    assert rv.status_code == 200
    assert rv.data.startswith(b'%PDF')


def test_export_pdf_dienste_empty_state_still_valid_pdf(export_client, instance):
    """Kein Termin/Schicht vorhanden -> Platzhaltertext statt Absturz."""
    rv = export_client.get(f'/api/admin/{instance.slug}/export/pdf/dienste')
    assert rv.status_code == 200
    assert rv.data.startswith(b'%PDF')


def test_export_pdf_essen_empty_state_still_valid_pdf(export_client, instance):
    """Keine Essensspendenart vorhanden -> Platzhaltertext statt Absturz."""
    rv = export_client.get(f'/api/admin/{instance.slug}/export/pdf/essen')
    assert rv.status_code == 200
    assert rv.data.startswith(b'%PDF')


def test_export_pdf_essen_food_type_without_donations_still_valid_pdf(export_client, instance):
    """Spendenart ohne bisherige Spenden -> Platzhalterzeile statt Absturz."""
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 2), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    ft = FoodDonationType(instance_id=instance.id, event_date_id=ed.id, name='Salate',
                          refrigeration_enabled=False)
    _db.session.add(ft)
    _db.session.commit()

    rv = export_client.get(f'/api/admin/{instance.slug}/export/pdf/essen')
    assert rv.status_code == 200
    assert rv.data.startswith(b'%PDF')


def test_export_pdf_legacy_shift_without_registrations_still_valid_pdf(export_client, instance):
    """Schicht ohne Anmeldung -> Platzhalterzeile statt Absturz."""
    ed = EventDate(instance_id=instance.id, date=date(2026, 9, 3), is_draft=False)
    _db.session.add(ed)
    _db.session.flush()
    stand = Stand(instance_id=instance.id, name='Unbesetzter Stand', sort_order=0)
    _db.session.add(stand)
    _db.session.flush()
    shift = Shift(stand_id=stand.id, event_date_id=ed.id,
                  start_time=time(9, 0), end_time=time(12, 0), max_volunteers=2)
    _db.session.add(shift)
    _db.session.commit()

    rv = export_client.get(f'/api/admin/{instance.slug}/export/pdf')
    assert rv.status_code == 200
    assert rv.data.startswith(b'%PDF')


# ---------------------------------------------------------------------------
# PDF – Dienste / Essen (POST, date_ids-Filter + optionaler Mail-Versand)
# ---------------------------------------------------------------------------

def test_export_pdf_dienste_post_requires_date_ids(export_client, instance):
    rv = export_client.post(f'/api/admin/{instance.slug}/export/pdf/dienste', json={})
    assert rv.status_code == 422


def test_export_pdf_dienste_post_returns_pdf_without_email(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.post(
        f'/api/admin/{instance.slug}/export/pdf/dienste',
        json={'date_ids': [export_setup['event_date'].id]},
    )
    assert rv.status_code == 200
    assert rv.mimetype == 'application/pdf'
    assert rv.data.startswith(b'%PDF')


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_export_pdf_dienste_post_sends_email_when_configured(mock_configured, mock_send, export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.post(
        f'/api/admin/{instance.slug}/export/pdf/dienste',
        json={'date_ids': [export_setup['event_date'].id], 'email': 'empfaenger@test.de'},
    )
    assert rv.status_code == 200
    assert 'empfaenger@test.de' in rv.get_json()['message']
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs['to'] == 'empfaenger@test.de'
    assert mock_send.call_args.kwargs['attachments'][0][1] == 'application/pdf'


@patch('app.utils.mail.is_mail_configured', return_value=False)
def test_export_pdf_dienste_post_email_without_mail_config_returns_503(mock_configured, export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.post(
        f'/api/admin/{instance.slug}/export/pdf/dienste',
        json={'date_ids': [export_setup['event_date'].id], 'email': 'empfaenger@test.de'},
    )
    assert rv.status_code == 503


def test_export_pdf_essen_post_requires_date_ids(export_client, instance):
    rv = export_client.post(f'/api/admin/{instance.slug}/export/pdf/essen', json={})
    assert rv.status_code == 422


def test_export_pdf_essen_post_returns_pdf_without_email(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.post(
        f'/api/admin/{instance.slug}/export/pdf/essen',
        json={'date_ids': [export_setup['event_date'].id]},
    )
    assert rv.status_code == 200
    assert rv.data.startswith(b'%PDF')


@patch('app.utils.mail.send_mail')
@patch('app.utils.mail.is_mail_configured', return_value=True)
def test_export_pdf_essen_post_sends_email_when_configured(mock_configured, mock_send, export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.post(
        f'/api/admin/{instance.slug}/export/pdf/essen',
        json={'date_ids': [export_setup['event_date'].id], 'email': 'empfaenger@test.de'},
    )
    assert rv.status_code == 200
    mock_send.assert_called_once()


# ---------------------------------------------------------------------------
# iCal
# ---------------------------------------------------------------------------

def test_export_ical_contains_events_for_shifts(export_client, export_setup):
    instance = export_setup['instance']
    rv = export_client.get(f'/api/admin/{instance.slug}/export/ical')
    assert rv.status_code == 200
    assert rv.mimetype == 'text/calendar'
    cal = Calendar.from_ical(rv.data)
    events = [c for c in cal.walk() if c.name == 'VEVENT']
    assert len(events) == 1
    assert 'Grillstand' in str(events[0]['summary'])
    assert export_setup['volunteer'].name in str(events[0]['description'])


def test_export_ical_empty_state_has_no_events(export_client, instance):
    rv = export_client.get(f'/api/admin/{instance.slug}/export/ical')
    assert rv.status_code == 200
    cal = Calendar.from_ical(rv.data)
    events = [c for c in cal.walk() if c.name == 'VEVENT']
    assert events == []


# ---------------------------------------------------------------------------
# _pdf_branding – deaktiviertes Branding liefert leeren Footer
# ---------------------------------------------------------------------------

def test_pdf_branding_disabled_returns_empty(app, instance):
    from flask import g as _g
    _db.session.execute(
        SiteSettings.__table__.update()
        .where(SiteSettings.instance_id == instance.id)
        .values(branding_enabled=False)
    )
    _db.session.commit()
    with app.test_request_context():
        _g.instance = instance
        result = _pdf_branding()
    assert result == {'css': '', 'html': ''}
