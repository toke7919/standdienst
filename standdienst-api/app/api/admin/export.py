import csv
import io
from datetime import date, datetime, timezone

from flask import g, request, send_file, current_app
from icalendar import Calendar, Event
import pytz

from . import admin_bp
from ...extensions import db
from ...models import Instance, Stand, EventDate, Shift, Registration, Volunteer, FoodDonation, FoodDonationType
from ...utils.auth import require_staff, require_admin
from ...utils.responses import error


# ---------------------------------------------------------------------------
# CSV – Shifts/Registrations
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/csv/registrations', methods=['GET'])
@require_staff
def export_csv_registrations(slug):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Stand', 'Datum', 'Uhrzeit', 'Helfer', 'E-Mail', 'Angemeldet am'])

    shifts = (Shift.query
              .join(Stand, Stand.id == Shift.stand_id)
              .filter(Stand.instance_id == g.instance.id)
              .order_by(Shift.event_date_id, Stand.sort_order)
              .all())

    for shift in shifts:
        for reg in shift.registrations:
            v = reg.volunteer
            writer.writerow([
                shift.stand.name,
                shift.event_date.formatted,
                shift.time_range,
                v.name,
                v.email or '',
                reg.registered_at.strftime('%d.%m.%Y %H:%M') if reg.registered_at else '',
            ])

    output.seek(0)
    filename = f'anmeldungen_{g.instance.slug}_{date.today()}.csv'
    return send_file(
        io.BytesIO(('﻿' + output.getvalue()).encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


@admin_bp.route('/<slug>/export/csv/volunteers', methods=['GET'])
@require_staff
def export_csv_volunteers(slug):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Name', 'E-Mail', 'Angemeldet', 'Schichten'])

    volunteers = (Volunteer.query
                  .filter_by(instance_id=g.instance.id)
                  .filter(Volunteer.deleted_at.is_(None))
                  .order_by(Volunteer.name)
                  .all())

    for v in volunteers:
        shift_count = v.registrations.count()
        writer.writerow([
            v.name,
            v.email or '',
            v.created_at.strftime('%d.%m.%Y') if v.created_at else '',
            shift_count,
        ])

    output.seek(0)
    filename = f'helfer_{g.instance.slug}_{date.today()}.csv'
    return send_file(
        io.BytesIO(('﻿' + output.getvalue()).encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename,
    )


# ---------------------------------------------------------------------------
# ODS – Schichtplan
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/ods', methods=['GET'])
@require_staff
def export_ods(slug):
    try:
        from odf.opendocument import OpenDocumentSpreadsheet
        from odf.table import Table, TableRow, TableCell
        from odf.text import P
        from odf.style import Style, TextProperties, TableCellProperties
    except ImportError:
        return error('odfpy nicht installiert', 500)

    doc = OpenDocumentSpreadsheet()

    def make_header_style():
        s = Style(name='HeaderStyle', family='table-cell')
        s.addElement(TableCellProperties(backgroundcolor='#4f46e5'))
        s.addElement(TextProperties(fontweight='bold', color='#ffffff'))
        doc.styles.addElement(s)
        return s

    hstyle = make_header_style()

    def add_cell(row, text, style=None):
        cell = TableCell(stylename=style)
        cell.addElement(P(text=str(text or '')))
        row.addElement(cell)

    sheet = Table(name='Anmeldungen')

    # Header
    header_row = TableRow()
    for col in ['Stand', 'Datum', 'Uhrzeit', 'Helfer', 'E-Mail', 'Angemeldet am']:
        add_cell(header_row, col, hstyle)
    sheet.addElement(header_row)

    shifts = (Shift.query
              .join(Stand, Stand.id == Shift.stand_id)
              .filter(Stand.instance_id == g.instance.id)
              .order_by(Shift.event_date_id, Stand.sort_order)
              .all())

    for shift in shifts:
        for reg in shift.registrations:
            v = reg.volunteer
            row = TableRow()
            add_cell(row, shift.stand.name)
            add_cell(row, shift.event_date.formatted)
            add_cell(row, shift.time_range)
            add_cell(row, v.name)
            add_cell(row, v.email or '')
            add_cell(row, reg.registered_at.strftime('%d.%m.%Y %H:%M') if reg.registered_at else '')
            sheet.addElement(row)

    doc.spreadsheet.addElement(sheet)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    filename = f'schichtplan_{g.instance.slug}_{date.today()}.ods'
    return send_file(buf, mimetype='application/vnd.oasis.opendocument.spreadsheet',
                     as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# PDF – Schichtplan via WeasyPrint
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/pdf', methods=['GET'])
@require_staff
def export_pdf(slug):
    try:
        from weasyprint import HTML
    except ImportError:
        return error('WeasyPrint nicht installiert', 500)

    shifts = (Shift.query
              .join(Stand, Stand.id == Shift.stand_id)
              .filter(Stand.instance_id == g.instance.id)
              .order_by(Shift.event_date_id, Stand.sort_order)
              .all())

    rows_html = ''
    for shift in shifts:
        regs = list(shift.registrations)
        if not regs:
            rows_html += _pdf_row(shift.stand.name, shift.event_date.formatted,
                                   shift.time_range, '—', '')
        for reg in regs:
            rows_html += _pdf_row(shift.stand.name, shift.event_date.formatted,
                                   shift.time_range, reg.volunteer.name,
                                   reg.volunteer.email or '')

    html_content = f'''
    <html><head><style>
      body {{ font-family: Arial, sans-serif; font-size: 10pt; }}
      h1 {{ color: #4f46e5; }}
      table {{ width: 100%; border-collapse: collapse; }}
      th {{ background: #4f46e5; color: white; padding: 6px; text-align: left; }}
      td {{ padding: 5px; border-bottom: 1px solid #eee; }}
      tr:nth-child(even) td {{ background: #f9f9f9; }}
    </style></head><body>
      <h1>Schichtplan – {g.instance.name}</h1>
      <p>Exportiert am {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
      <table>
        <tr><th>Stand</th><th>Datum</th><th>Uhrzeit</th><th>Helfer</th><th>E-Mail</th></tr>
        {rows_html}
      </table>
    </body></html>'''

    buf = io.BytesIO()
    HTML(string=html_content).write_pdf(buf)
    buf.seek(0)
    filename = f'schichtplan_{g.instance.slug}_{date.today()}.pdf'
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)


def _pdf_row(stand, datum, uhrzeit, name, email):
    return (f'<tr><td>{stand}</td><td>{datum}</td><td>{uhrzeit}</td>'
            f'<td>{name}</td><td>{email}</td></tr>')


# ---------------------------------------------------------------------------
# iCal – Schichten
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/ical', methods=['GET'])
@require_staff
def export_ical(slug):
    cal = Calendar()
    cal.add('prodid', f'-//Standdienst//{g.instance.slug}//DE')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', f'Schichtplan {g.instance.name}')

    tz = pytz.timezone('Europe/Berlin')

    shifts = (Shift.query
              .join(Stand, Stand.id == Shift.stand_id)
              .filter(Stand.instance_id == g.instance.id)
              .all())

    for shift in shifts:
        regs = list(shift.registrations)
        summary = f'{shift.stand.name}: {shift.time_range}'
        helpers = ', '.join(r.volunteer.name for r in regs) if regs else 'Keine Anmeldungen'

        event = Event()
        event.add('summary', summary)
        event.add('description', f'Helfer: {helpers}')
        event.add('dtstart', tz.localize(datetime.combine(shift.event_date.date, shift.start_time)))
        event.add('dtend', tz.localize(datetime.combine(shift.event_date.date, shift.end_time)))
        event.add('uid', f'shift-{shift.id}@standdienst')
        cal.add_component(event)

    buf = io.BytesIO(cal.to_ical())
    filename = f'schichtplan_{g.instance.slug}_{date.today()}.ics'
    return send_file(buf, mimetype='text/calendar', as_attachment=True, download_name=filename)
