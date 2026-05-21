import csv
import io
from datetime import date, datetime, timezone

from flask import g, request, send_file, current_app
from icalendar import Calendar, Event
import pytz

from . import admin_bp
from ...extensions import db
from ...models import (
    Instance, Stand, EventDate, Shift, Registration,
    Volunteer, FoodDonation, FoodDonationType,
)
from ...utils.auth import require_staff, require_admin
from ...utils.responses import error


def _vol_name(reg):
    v = reg.volunteer
    return v.name if v else (reg.guest_name or '—')


def _vol_email(reg):
    v = reg.volunteer
    return v.email or '' if v else ''


def _food_name(don):
    v = don.volunteer
    return v.name if v else (don.guest_name or '—')


def _food_email(don):
    v = don.volunteer
    return v.email or '' if v else ''


def _primary_color():
    from ...models import SiteSettings
    s = SiteSettings.query.filter_by(instance_id=g.instance.id).first()
    return s.primary_color if s and s.primary_color else '#4f46e5'


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
            writer.writerow([
                shift.stand.name,
                shift.event_date.formatted,
                shift.time_range,
                _vol_name(reg),
                _vol_email(reg),
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
    writer.writerow(['Name', 'E-Mail', 'Angemeldet', 'Dienste'])

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
# ODS – Dienste (eine Tabelle je Tag)
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/ods/dienste', methods=['GET'])
@require_staff
def export_ods_dienste(slug):
    try:
        from odf.opendocument import OpenDocumentSpreadsheet
        from odf.table import Table, TableRow, TableCell
        from odf.text import P
        from odf.style import Style, TextProperties, TableCellProperties
    except ImportError:
        return error('odfpy nicht installiert', 500)

    color = _primary_color()
    doc = OpenDocumentSpreadsheet()

    def make_header_style():
        s = Style(name='HeaderStyle', family='table-cell')
        s.addElement(TableCellProperties(backgroundcolor=color))
        s.addElement(TextProperties(fontweight='bold', color='#ffffff'))
        doc.styles.addElement(s)
        return s

    hstyle = make_header_style()

    def add_cell(row, text, style=None):
        cell = TableCell(stylename=style)
        cell.addElement(P(text=str(text or '')))
        row.addElement(cell)

    event_dates = (EventDate.query
                   .join(Shift, Shift.event_date_id == EventDate.id)
                   .join(Stand, Stand.id == Shift.stand_id)
                   .filter(Stand.instance_id == g.instance.id)
                   .distinct()
                   .order_by(EventDate.date)
                   .all())

    if not event_dates:
        event_dates_fallback = (EventDate.query
                                .filter_by(instance_id=g.instance.id)
                                .order_by(EventDate.date)
                                .all())
        event_dates = event_dates_fallback

    for ed in event_dates:
        sheet_name = ed.date.strftime('%d.%m.%Y')
        sheet = Table(name=sheet_name)

        header_row = TableRow()
        for col in ['Stand', 'Uhrzeit', 'Helfer', 'E-Mail']:
            add_cell(header_row, col, hstyle)
        sheet.addElement(header_row)

        shifts = (Shift.query
                  .join(Stand, Stand.id == Shift.stand_id)
                  .filter(Stand.instance_id == g.instance.id,
                          Shift.event_date_id == ed.id)
                  .order_by(Stand.sort_order, Shift.start_time)
                  .all())

        for shift in shifts:
            regs = list(shift.registrations)
            if not regs:
                row = TableRow()
                add_cell(row, shift.stand.name)
                add_cell(row, shift.time_range)
                add_cell(row, '—')
                add_cell(row, '')
                sheet.addElement(row)
            for reg in regs:
                row = TableRow()
                add_cell(row, shift.stand.name)
                add_cell(row, shift.time_range)
                add_cell(row, _vol_name(reg))
                add_cell(row, _vol_email(reg))
                sheet.addElement(row)

        doc.spreadsheet.addElement(sheet)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    filename = f'dienste_{g.instance.slug}_{date.today()}.ods'
    return send_file(buf, mimetype='application/vnd.oasis.opendocument.spreadsheet',
                     as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# ODS – Essensspenden (eine Tabelle je Spendenart)
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/ods/essen', methods=['GET'])
@require_staff
def export_ods_essen(slug):
    try:
        from odf.opendocument import OpenDocumentSpreadsheet
        from odf.table import Table, TableRow, TableCell
        from odf.text import P
        from odf.style import Style, TextProperties, TableCellProperties
    except ImportError:
        return error('odfpy nicht installiert', 500)

    color = _primary_color()
    doc = OpenDocumentSpreadsheet()

    def make_header_style():
        s = Style(name='HeaderStyle', family='table-cell')
        s.addElement(TableCellProperties(backgroundcolor=color))
        s.addElement(TextProperties(fontweight='bold', color='#ffffff'))
        doc.styles.addElement(s)
        return s

    hstyle = make_header_style()

    def add_cell(row, text, style=None):
        cell = TableCell(stylename=style)
        cell.addElement(P(text=str(text or '')))
        row.addElement(cell)

    food_types = (FoodDonationType.query
                  .filter_by(instance_id=g.instance.id)
                  .order_by(FoodDonationType.event_date_id, FoodDonationType.name)
                  .all())

    for ft in food_types:
        sheet_name = ft.name[:28]
        sheet = Table(name=sheet_name)

        header_row = TableRow()
        for col in ['Helfer', 'E-Mail', 'Was wird mitgebracht', 'Kühlpflichtig']:
            add_cell(header_row, col, hstyle)
        sheet.addElement(header_row)

        donations = list(ft.donations.order_by(FoodDonation.registered_at))
        if not donations:
            row = TableRow()
            add_cell(row, '—')
            add_cell(row, '')
            add_cell(row, '')
            add_cell(row, '')
            sheet.addElement(row)
        for don in donations:
            row = TableRow()
            add_cell(row, _food_name(don))
            add_cell(row, _food_email(don))
            add_cell(row, don.description)
            add_cell(row, 'Ja' if don.needs_refrigeration else 'Nein')
            sheet.addElement(row)

        doc.spreadsheet.addElement(sheet)

    if not food_types:
        sheet = Table(name='Essensspenden')
        doc.spreadsheet.addElement(sheet)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    filename = f'essensspenden_{g.instance.slug}_{date.today()}.ods'
    return send_file(buf, mimetype='application/vnd.oasis.opendocument.spreadsheet',
                     as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# ODS – Alle Anmeldungen (Legacy, eine Tabelle)
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
            row = TableRow()
            add_cell(row, shift.stand.name)
            add_cell(row, shift.event_date.formatted)
            add_cell(row, shift.time_range)
            add_cell(row, _vol_name(reg))
            add_cell(row, _vol_email(reg))
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
# PDF – Dienste (eine Seite je Tag)
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/pdf/dienste', methods=['GET'])
@require_staff
def export_pdf_dienste(slug):
    try:
        from weasyprint import HTML
    except ImportError:
        return error('WeasyPrint nicht installiert', 500)

    color = _primary_color()

    event_dates = (EventDate.query
                   .join(Shift, Shift.event_date_id == EventDate.id)
                   .join(Stand, Stand.id == Shift.stand_id)
                   .filter(Stand.instance_id == g.instance.id)
                   .distinct()
                   .order_by(EventDate.date)
                   .all())

    sections = ''
    for i, ed in enumerate(event_dates):
        break_style = 'page-break-before: always;' if i > 0 else ''

        shifts = (Shift.query
                  .join(Stand, Stand.id == Shift.stand_id)
                  .filter(Stand.instance_id == g.instance.id,
                          Shift.event_date_id == ed.id)
                  .order_by(Stand.sort_order, Shift.start_time)
                  .all())

        rows = ''
        for shift in shifts:
            regs = list(shift.registrations)
            if not regs:
                rows += (f'<tr><td>{shift.stand.name}</td><td>{shift.time_range}</td>'
                         f'<td>—</td><td></td></tr>')
            for reg in regs:
                rows += (f'<tr><td>{shift.stand.name}</td><td>{shift.time_range}</td>'
                         f'<td>{_vol_name(reg)}</td><td>{_vol_email(reg)}</td></tr>')

        sections += f'''
        <div style="{break_style}">
          <h2 style="color:{color};margin:0 0 12px;font-size:14pt;">{ed.formatted}</h2>
          <table>
            <tr><th>Stand</th><th>Uhrzeit</th><th>Helfer</th><th>E-Mail</th></tr>
            {rows}
          </table>
        </div>'''

    html_content = f'''
    <html><head><style>
      body {{ font-family: Arial, sans-serif; font-size: 10pt; margin: 1.5cm; }}
      h1 {{ color: {color}; margin: 0 0 4px; font-size: 16pt; }}
      h2 {{ color: {color}; margin: 0 0 12px; font-size: 14pt; }}
      p.meta {{ color: #6b7280; font-size: 9pt; margin: 0 0 20px; }}
      table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
      th {{ background: {color}; color: white; padding: 6px 8px; text-align: left; font-size: 9pt; }}
      td {{ padding: 5px 8px; border-bottom: 1px solid #e5e7eb; font-size: 9pt; }}
      tr:nth-child(even) td {{ background: #f9fafb; }}
    </style></head><body>
      <h1>Dienstplan – {g.instance.name}</h1>
      <p class="meta">Exportiert am {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
      {sections}
    </body></html>'''

    buf = io.BytesIO()
    HTML(string=html_content).write_pdf(buf)
    buf.seek(0)
    filename = f'dienste_{g.instance.slug}_{date.today()}.pdf'
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# PDF – Essensspenden (eine Seite je Spendenart)
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/pdf/essen', methods=['GET'])
@require_staff
def export_pdf_essen(slug):
    try:
        from weasyprint import HTML
    except ImportError:
        return error('WeasyPrint nicht installiert', 500)

    color = _primary_color()
    tz_name = 'Europe/Berlin'
    try:
        from ...utils.settings_cache import get_global_settings
        gs = get_global_settings()
        if gs and gs.timezone:
            tz_name = gs.timezone
    except Exception:
        pass
    tz = pytz.timezone(tz_name)

    food_types = (FoodDonationType.query
                  .filter_by(instance_id=g.instance.id)
                  .order_by(FoodDonationType.event_date_id, FoodDonationType.name)
                  .all())

    sections = ''
    for i, ft in enumerate(food_types):
        break_style = 'page-break-before: always;' if i > 0 else ''

        delivery_info = ''
        if ft.delivery_datetime:
            delivery_info += ft.delivery_datetime.astimezone(tz).strftime('%d.%m.%Y %H:%M')
        if ft.delivery_location:
            delivery_info += (' · ' if delivery_info else '') + ft.delivery_location

        donations = list(ft.donations.order_by(FoodDonation.registered_at))
        rows = ''
        if not donations:
            rows = '<tr><td>—</td><td></td><td></td><td></td></tr>'
        for don in donations:
            refrig = 'Ja' if don.needs_refrigeration else 'Nein'
            rows += (f'<tr><td>{_food_name(don)}</td><td>{_food_email(don)}</td>'
                     f'<td>{don.description}</td><td>{refrig}</td></tr>')

        info_line = f'<p class="meta">{delivery_info}</p>' if delivery_info else ''

        sections += f'''
        <div style="{break_style}">
          <h2 style="color:{color};margin:0 0 4px;font-size:14pt;">{ft.name}</h2>
          {info_line}
          <table>
            <tr><th>Helfer</th><th>E-Mail</th><th>Was wird mitgebracht</th><th>Kühlpflichtig</th></tr>
            {rows}
          </table>
        </div>'''

    if not sections:
        sections = '<p>Keine Essensspenden vorhanden.</p>'

    html_content = f'''
    <html><head><style>
      body {{ font-family: Arial, sans-serif; font-size: 10pt; margin: 1.5cm; }}
      h1 {{ color: {color}; margin: 0 0 4px; font-size: 16pt; }}
      h2 {{ color: {color}; margin: 0 0 4px; font-size: 14pt; }}
      p.meta {{ color: #6b7280; font-size: 9pt; margin: 0 0 12px; }}
      table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
      th {{ background: {color}; color: white; padding: 6px 8px; text-align: left; font-size: 9pt; }}
      td {{ padding: 5px 8px; border-bottom: 1px solid #e5e7eb; font-size: 9pt; }}
      tr:nth-child(even) td {{ background: #f9fafb; }}
    </style></head><body>
      <h1>Essensspenden – {g.instance.name}</h1>
      <p class="meta">Exportiert am {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
      {sections}
    </body></html>'''

    buf = io.BytesIO()
    HTML(string=html_content).write_pdf(buf)
    buf.seek(0)
    filename = f'essensspenden_{g.instance.slug}_{date.today()}.pdf'
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# PDF – Alle Anmeldungen (Legacy, eine Tabelle)
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
                                   shift.time_range, _vol_name(reg), _vol_email(reg))

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
        helpers = (', '.join(_vol_name(r) for r in regs)
                   if regs else 'Keine Anmeldungen')

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
