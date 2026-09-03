"""Funktionale Tests für app/api/admin/import_.py.

Autorisierung (@require_staff, Instanz-Zugriffsschutz) ist bereits in
test_authz_export_import.py abgedeckt. Anders als update.py/backup.py enthält
dieses Modul keine Subprocess-/Netzwerk-Operationen – es parst hochgeladene
Dateien (CSV/XLSX/ODS) rein im Speicher, daher kein spezielles Mocking nötig.

Hinweis (nicht behoben, nur für Transparenz): Volunteer, Registration und
ValidationError werden importiert, aber nirgends im Modul verwendet – toter
Import.
"""
import csv
import io

import openpyxl
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableRow, TableCell
from odf.text import P

from app.extensions import db as _db
from app.models import Stand, EventDate, Shift
from app.api.admin.import_ import _parse_date, _parse_time, _process_shift_rows
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


_HEADER = ['Stand', 'Datum (TT.MM.JJJJ)', 'Von (HH:MM)', 'Bis (HH:MM)', 'Max. Helfer']


def _csv_bytes(rows):
    out = io.StringIO()
    writer = csv.writer(out, delimiter=';')
    writer.writerow(_HEADER)
    for row in rows:
        writer.writerow(row)
    return ('﻿' + out.getvalue()).encode('utf-8')


def _xlsx_bytes(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(_HEADER)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def _ods_bytes(rows):
    doc = OpenDocumentSpreadsheet()
    table = Table(name='Dienste')
    for row_data in [_HEADER] + rows:
        row = TableRow()
        for val in row_data:
            cell = TableCell(valuetype='string')
            cell.addElement(P(text=str(val)))
            row.addElement(cell)
        table.addElement(row)
    doc.spreadsheet.addElement(table)
    buf = io.BytesIO()
    doc.write(buf)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# _parse_date / _parse_time – reine Funktionen
# ---------------------------------------------------------------------------

def test_parse_date_accepts_common_formats():
    from datetime import date
    assert _parse_date('23.05.2026') == date(2026, 5, 23)
    assert _parse_date('23.05.26') == date(2026, 5, 23)
    assert _parse_date('2026-05-23') == date(2026, 5, 23)
    assert _parse_date('23/05/2026') == date(2026, 5, 23)


def test_parse_date_unknown_format_raises():
    try:
        _parse_date('nicht-ein-datum')
        assert False, 'ValueError erwartet'
    except ValueError as e:
        assert 'Unbekanntes Datumsformat' in str(e)


def test_parse_time_strips_seconds():
    from datetime import time as dtime
    assert _parse_time('08:00:00') == dtime(8, 0)
    assert _parse_time('8:5') == dtime(8, 5)


# ---------------------------------------------------------------------------
# _process_shift_rows – direkte Unit-Tests der Verarbeitungslogik
# ---------------------------------------------------------------------------

def test_process_shift_rows_creates_stand_and_event_date_if_missing(app, instance):
    rows = [{'Stand': 'Neuer Stand', 'Datum (TT.MM.JJJJ)': '01.08.2026',
            'Von (HH:MM)': '08:00', 'Bis (HH:MM)': '12:00', 'Max. Helfer': '3'}]
    rv, status = _process_shift_rows(rows, instance.id)
    assert status == 200
    body = rv.get_json()['data']
    assert body['created'] == 1
    assert body['skipped'] == 0
    assert body['errors'] == []

    stand = _db.session.query(Stand).filter_by(instance_id=instance.id, name='Neuer Stand').first()
    assert stand is not None
    shift = _db.session.query(Shift).filter_by(stand_id=stand.id).first()
    assert shift.max_volunteers == 3


def test_process_shift_rows_skips_existing_duplicate(app, instance):
    row = {'Stand': 'Kasse', 'Datum (TT.MM.JJJJ)': '01.08.2026',
          'Von (HH:MM)': '08:00', 'Bis (HH:MM)': '12:00', 'Max. Helfer': '2'}
    _process_shift_rows([row], instance.id)
    rv, status = _process_shift_rows([row], instance.id)
    body = rv.get_json()['data']
    assert body['created'] == 0
    assert body['skipped'] == 1


def test_process_shift_rows_skips_empty_rows(app, instance):
    rv, status = _process_shift_rows([{'Stand': '', 'Datum (TT.MM.JJJJ)': '',
                                       'Von (HH:MM)': '', 'Bis (HH:MM)': ''}], instance.id)
    body = rv.get_json()['data']
    assert body['created'] == 0
    assert body['skipped'] == 0
    assert body['errors'] == []


def test_process_shift_rows_collects_error_without_stopping(app, instance):
    rows = [
        {'Stand': 'Kasse', 'Datum (TT.MM.JJJJ)': 'kein-datum',
         'Von (HH:MM)': '08:00', 'Bis (HH:MM)': '12:00', 'Max. Helfer': '2'},
        {'Stand': 'Kasse', 'Datum (TT.MM.JJJJ)': '01.08.2026',
         'Von (HH:MM)': '08:00', 'Bis (HH:MM)': '12:00', 'Max. Helfer': '2'},
    ]
    rv, status = _process_shift_rows(rows, instance.id)
    body = rv.get_json()['data']
    assert body['created'] == 1
    assert len(body['errors']) == 1
    assert 'Zeile 2' in body['errors'][0]


def test_process_shift_rows_non_digit_max_volunteers_defaults_to_two(app, instance):
    row = {'Stand': 'Kasse', 'Datum (TT.MM.JJJJ)': '01.08.2026',
          'Von (HH:MM)': '08:00', 'Bis (HH:MM)': '12:00', 'Max. Helfer': 'viele'}
    _process_shift_rows([row], instance.id)
    shift = _db.session.query(Shift).join(Stand).filter(Stand.instance_id == instance.id).first()
    assert shift.max_volunteers == 2


# ---------------------------------------------------------------------------
# GET /import/template/*
# ---------------------------------------------------------------------------

def test_import_template_csv_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.get(f'/api/admin/{instance.slug}/import/template/csv')
    assert rv.status_code == 200
    assert rv.mimetype == 'text/csv'
    assert b'Stand' in rv.data


def test_import_template_ods_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.get(f'/api/admin/{instance.slug}/import/template/ods')
    assert rv.status_code == 200
    assert rv.data.startswith(b'PK')  # ODS ist ein ZIP-Container


def test_import_template_xlsx_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.get(f'/api/admin/{instance.slug}/import/template/xlsx')
    assert rv.status_code == 200
    assert rv.data.startswith(b'PK')  # XLSX ist ebenfalls ein ZIP-Container


# ---------------------------------------------------------------------------
# POST /import/shifts/csv
# ---------------------------------------------------------------------------

def test_import_csv_no_file_returns_400(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/import/shifts/csv', data={})
    assert rv.status_code == 400


def test_import_csv_too_large_returns_400(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    oversized = b'x' * (2 * 1024 * 1024 + 1)
    rv = c.post(f'/api/admin/{instance.slug}/import/shifts/csv', data={
        'file': (io.BytesIO(oversized), 'gross.csv'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 400


def test_import_csv_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    content = _csv_bytes([['Kasse', '01.08.2026', '08:00', '12:00', '3']])
    rv = c.post(f'/api/admin/{instance.slug}/import/shifts/csv', data={
        'file': (io.BytesIO(content), 'schichten.csv'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['created'] == 1
    assert 'importiert' in rv.get_json()['message']


# ---------------------------------------------------------------------------
# POST /import/shifts/xlsx
# ---------------------------------------------------------------------------

def test_import_xlsx_no_file_returns_400(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/import/shifts/xlsx', data={})
    assert rv.status_code == 400


def test_import_xlsx_too_large_returns_400(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    oversized = b'x' * (2 * 1024 * 1024 + 1)
    rv = c.post(f'/api/admin/{instance.slug}/import/shifts/xlsx', data={
        'file': (io.BytesIO(oversized), 'gross.xlsx'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 400


def test_import_xlsx_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    content = _xlsx_bytes([['Kasse', '01.08.2026', '08:00', '12:00', 3]])
    rv = c.post(f'/api/admin/{instance.slug}/import/shifts/xlsx', data={
        'file': (io.BytesIO(content), 'schichten.xlsx'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert rv.get_json()['data']['created'] == 1


# ---------------------------------------------------------------------------
# POST /import/shifts/ods
# ---------------------------------------------------------------------------

def test_import_ods_no_file_returns_400(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/import/shifts/ods', data={})
    assert rv.status_code == 400


def test_import_ods_too_large_returns_400(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    oversized = b'x' * (2 * 1024 * 1024 + 1)
    rv = c.post(f'/api/admin/{instance.slug}/import/shifts/ods', data={
        'file': (io.BytesIO(oversized), 'gross.ods'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 400


def test_import_ods_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    content = _ods_bytes([['Kasse', '01.08.2026', '08:00', '12:00', '3']])
    rv = c.post(f'/api/admin/{instance.slug}/import/shifts/ods', data={
        'file': (io.BytesIO(content), 'schichten.ods'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert rv.get_json()['data']['created'] == 1
