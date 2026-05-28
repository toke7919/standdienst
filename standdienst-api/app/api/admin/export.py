import csv
import io
from collections import defaultdict
from datetime import date, datetime, timezone

from flask import g, request, send_file, current_app
from icalendar import Calendar, Event
import pytz
from sqlalchemy import select

from . import admin_bp
from ...extensions import db
from ...models import (
    Instance, Stand, EventDate, Shift, Registration,
    Volunteer, FoodDonation, FoodDonationType,
)
from ...utils.auth import require_staff, require_admin
from ...utils.responses import error, ok


def _vol_name(reg):
    v = reg.volunteer
    return v.name if v else (reg.guest_name or '—')


def _food_name(don):
    v = don.volunteer
    return v.name if v else (don.guest_name or '—')


def _sender_name(user) -> str:
    fn = (getattr(user, 'first_name', None) or '').strip()
    ln = (getattr(user, 'last_name', None) or '').strip()
    full = f'{fn} {ln}'.strip()
    return full or getattr(user, 'name', None) or ''


def _date_summary(ed) -> str:
    s = ed.formatted
    if ed.label:
        s += f' – {ed.label}'
    return s


def _primary_color():
    from ...models import SiteSettings
    s = db.session.scalars(select(SiteSettings).filter_by(instance_id=g.instance.id)).first()
    return s.primary_color if s and s.primary_color else '#a51f2c'


def _pdf_branding() -> dict:
    """Gibt {'css': str, 'html': str} für den Seiten-Footer zurück.
    Beide Strings sind leer wenn branding_enabled=False."""
    from ...models import SiteSettings
    from ...utils.mail import get_platform_logo_for_email
    s = db.session.scalars(select(SiteSettings).filter_by(instance_id=g.instance.id)).first()
    if s is not None and not s.branding_enabled:
        return {'css': '', 'html': ''}
    logo = get_platform_logo_for_email() or ''
    logo_tag = (
        f'<img src="{logo}" alt="Standdienst"'
        f' style="height:13px;vertical-align:middle;margin-right:5px;">'
        if logo else ''
    )
    css = '''
      .pdf-brand { position: running(footer); background: #a51f2c; color: #ffffff;
                   text-align: center; padding: 2px 10px; font-size: 6.5pt;
                   font-family: Arial, sans-serif; white-space: nowrap; }
      @page { margin-bottom: 1.4cm; @bottom-center { content: element(footer); } }
    '''
    html = (
        f'<div class="pdf-brand">'
        f'{logo_tag}Erstellt mit <strong>Standdienst</strong>'
        f'</div>'
    )
    return {'css': css, 'html': html}


def _build_dienste_pdf_html(days: dict, color: str, brand: dict, instance_name: str) -> str:
    sections = ''
    for i, (ed, stands_map) in enumerate(days.items()):
        break_style = 'page-break-before: always;' if i > 0 else ''
        stand_tables = ''
        for stand, shifts in stands_map.items():
            rows = ''
            for sh in shifts:
                regs = list(sh.registrations)
                names = '<br>'.join(_vol_name(r) for r in regs) if regs else \
                        '<span style="color:#9ca3af">—</span>'
                rows += f'<tr><td class="time">{sh.time_range}</td><td>{names}</td></tr>'
            stand_tables += f'''
            <div style="margin-bottom:16px;">
              <p style="margin:0 0 4px;font-weight:700;font-size:11pt;color:#1f2937;">{stand.name}</p>
              <table>
                <thead><tr><th>Uhrzeit</th><th>Helfer</th></tr></thead>
                <tbody>{rows}</tbody>
              </table>
            </div>'''
        label_line = (f'<p style="color:#6b7280;font-size:10pt;font-weight:400;'
                      f'margin:0 0 12px;">{ed.label}</p>') if ed.label else ''
        sections += f'''
        <div style="{break_style} margin-bottom: 2em;">
          <h2 style="color:{color};margin:0 0 4px;font-size:14pt;font-weight:700;">
            {ed.formatted}
          </h2>
          {label_line}
          {stand_tables}
        </div>'''

    if not sections:
        sections = '<p>Keine Dienste vorhanden.</p>'

    return f'''
    <html><head><style>
      body {{ font-family: Arial, sans-serif; font-size: 10pt; margin: 1.5cm; }}
      h1 {{ color: {color}; margin: 0 0 4px; font-size: 16pt; font-weight: 800; }}
      h2 {{ color: {color}; font-size: 14pt; font-weight: 700; }}
      p.meta {{ color: #6b7280; font-size: 9pt; margin: 0 0 20px; }}
      table {{ width: 100%; border-collapse: collapse; margin-bottom: 4px; }}
      th {{ background: {color}; color: white; padding: 6px 10px; text-align: left;
            font-size: 9pt; font-weight: 700; }}
      td {{ padding: 7px 10px; border-bottom: 1px solid #e5e7eb; font-size: 11pt;
            vertical-align: top; }}
      td.time {{ font-size: 9pt; color: #4b5563; white-space: nowrap; font-weight: 600;
                 width: 1%; }}
      tr:nth-child(even) td {{ background: #f9fafb; }}
      {brand['css']}
    </style></head><body>
      {brand['html']}
      <h1>Dienstplan – {instance_name}</h1>
      <p class="meta">Exportiert am {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
      {sections}
    </body></html>'''


def _build_essen_pdf_html(food_types: list, color: str, brand: dict,
                           instance_name: str, tz) -> str:
    sections = ''
    for i, ft in enumerate(food_types):
        break_style = 'page-break-before: always;' if i > 0 else ''
        delivery_info = ''
        if ft.delivery_datetime:
            delivery_info += 'Abgabe: ' + ft.delivery_datetime.astimezone(tz).strftime('%d.%m.%Y %H:%M')
        if ft.delivery_location:
            delivery_info += (' · ' if delivery_info else '') + ft.delivery_location
        donations = list(ft.donations.order_by(FoodDonation.registered_at))
        rows = ''
        if not donations:
            rows = '<tr><td>—</td><td></td><td></td></tr>'
        for don in donations:
            refrig = 'Ja' if don.needs_refrigeration else 'Nein'
            rows += (f'<tr><td>{_food_name(don)}</td>'
                     f'<td>{don.description}</td><td>{refrig}</td></tr>')
        event_label = ft.event_date.label if ft.event_date and ft.event_date.label else ''
        date_formatted = ft.event_date.formatted if ft.event_date else ''
        date_heading = date_formatted + (f' – {event_label}' if event_label else '')
        heading = ft.name + (f' · {date_heading}' if date_heading else '')
        info_line = f'<p class="meta">{delivery_info}</p>' if delivery_info else ''
        sections += f'''
        <div style="{break_style}">
          <h2 style="color:{color};margin:0 0 2px;font-size:14pt;">{heading}</h2>
          {info_line}
          <table>
            <tr><th>Helfer</th><th>Was wird mitgebracht</th><th>Kühlpflichtig</th></tr>
            {rows}
          </table>
        </div>'''

    if not sections:
        sections = '<p>Keine Essensspenden vorhanden.</p>'

    return f'''
    <html><head><style>
      body {{ font-family: Arial, sans-serif; font-size: 10pt; margin: 1.5cm; }}
      h1 {{ color: {color}; margin: 0 0 4px; font-size: 16pt; }}
      h2 {{ color: {color}; margin: 0 0 2px; font-size: 14pt; }}
      p.meta {{ color: #6b7280; font-size: 9pt; margin: 0 0 12px; }}
      table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
      th {{ background: {color}; color: white; padding: 6px 8px; text-align: left; font-size: 9pt; }}
      td {{ padding: 5px 8px; border-bottom: 1px solid #e5e7eb; font-size: 9pt; }}
      tr:nth-child(even) td {{ background: #f9fafb; }}
      {brand['css']}
    </style></head><body>
      {brand['html']}
      <h1>Essensspenden – {instance_name}</h1>
      <p class="meta">Exportiert am {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
      {sections}
    </body></html>'''


# ---------------------------------------------------------------------------
# CSV – Shifts/Registrations
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/csv/registrations', methods=['GET'])
@require_staff
def export_csv_registrations(slug):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Stand', 'Datum', 'Uhrzeit', 'Helfer', 'E-Mail', 'Angemeldet am'])

    shifts = db.session.scalars(
        select(Shift)
        .join(Stand, Stand.id == Shift.stand_id)
        .filter(Stand.instance_id == g.instance.id)
        .order_by(Shift.event_date_id, Stand.sort_order)
    ).all()

    for shift in shifts:
        for reg in shift.registrations:
            v = reg.volunteer
            writer.writerow([
                shift.stand.name,
                shift.event_date.formatted,
                shift.time_range,
                _vol_name(reg),
                v.email or '' if v else '',
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

    volunteers = db.session.scalars(
        select(Volunteer)
        .filter_by(instance_id=g.instance.id)
        .filter(Volunteer.deleted_at.is_(None))
        .order_by(Volunteer.name)
    ).all()

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
# Hilfsfunktionen für Dienste-Exports
# ---------------------------------------------------------------------------

def _dienste_by_day(instance_id, date_ids=None):
    """Gibt {EventDate: {Stand: [Shift]}} zurück, geordnet nach Datum + sort_order."""
    q = (
        select(EventDate)
        .join(Shift, Shift.event_date_id == EventDate.id)
        .join(Stand, Stand.id == Shift.stand_id)
        .filter(Stand.instance_id == instance_id)
    )
    if date_ids:
        q = q.filter(EventDate.id.in_(date_ids))
    event_dates = db.session.scalars(
        q.distinct().order_by(EventDate.date)
    ).all()

    result = {}
    for ed in event_dates:
        stands_map = {}
        shifts = db.session.scalars(
            select(Shift)
            .join(Stand, Stand.id == Shift.stand_id)
            .filter(Stand.instance_id == instance_id,
                    Shift.event_date_id == ed.id)
            .order_by(Stand.sort_order, Shift.start_time)
        ).all()
        for shift in shifts:
            stands_map.setdefault(shift.stand, []).append(shift)
        if stands_map:
            result[ed] = stands_map
    return result


# ---------------------------------------------------------------------------
# ODS – Dienste (je Tag ein Blatt, je Blatt nach Ständen gruppiert)
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

    def make_style(name, bg, bold=False, color_txt='#111827', wrap=False):
        s = Style(name=name, family='table-cell')
        cell_props = {'backgroundcolor': bg}
        if wrap:
            cell_props['wrapoption'] = 'wrap'
        s.addElement(TableCellProperties(**cell_props))
        tp_attrs = {'color': color_txt}
        if bold:
            tp_attrs['fontweight'] = 'bold'
        s.addElement(TextProperties(**tp_attrs))
        doc.styles.addElement(s)
        return s

    hstyle = make_style('HeaderStyle', color, bold=True, color_txt='#ffffff')
    sstyle = make_style('StandStyle', '#f3f4f6', bold=True, color_txt='#1f2937')
    wstyle = make_style('WrapStyle', '#ffffff', wrap=True)

    def add_cell(row, text, style=None):
        cell = TableCell(stylename=style)
        cell.addElement(P(text=str(text or '')))
        row.addElement(cell)

    def add_multiline_cell(row, lines, style=None):
        cell = TableCell(stylename=style)
        for line in (lines or ['—']):
            cell.addElement(P(text=str(line)))
        row.addElement(cell)

    days = _dienste_by_day(g.instance.id)

    for ed, stands_map in days.items():
        sheet = Table(name=ed.date.strftime('%d.%m.%Y'))

        hr = TableRow()
        for col in ['Stand', 'Uhrzeit', 'Helfer']:
            add_cell(hr, col, hstyle)
        sheet.addElement(hr)

        for stand, shifts in stands_map.items():
            sr = TableRow()
            add_cell(sr, stand.name, sstyle)
            add_cell(sr, '', sstyle)
            add_cell(sr, '', sstyle)
            sheet.addElement(sr)

            for shift in shifts:
                regs = list(shift.registrations)
                names = [_vol_name(r) for r in regs] if regs else []
                row = TableRow()
                add_cell(row, '')
                add_cell(row, shift.time_range)
                add_multiline_cell(row, names, wstyle)
                sheet.addElement(row)

        doc.spreadsheet.addElement(sheet)

    if not days:
        doc.spreadsheet.addElement(Table(name='Dienste'))

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    filename = f'dienste_{g.instance.slug}_{date.today()}.ods'
    return send_file(buf, mimetype='application/vnd.oasis.opendocument.spreadsheet',
                     as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# ODS – Essensspenden (je Spendenart ein Blatt, ohne E-Mail)
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

    food_types = db.session.scalars(
        select(FoodDonationType)
        .filter_by(instance_id=g.instance.id)
        .order_by(FoodDonationType.event_date_id, FoodDonationType.name)
    ).all()

    for ft in food_types:
        sheet = Table(name=ft.name[:28])

        hr = TableRow()
        for col in ['Helfer', 'Was wird mitgebracht', 'Kühlpflichtig']:
            add_cell(hr, col, hstyle)
        sheet.addElement(hr)

        donations = list(ft.donations.order_by(FoodDonation.registered_at))
        if not donations:
            row = TableRow()
            add_cell(row, '—')
            add_cell(row, '')
            add_cell(row, '')
            sheet.addElement(row)
        for don in donations:
            row = TableRow()
            add_cell(row, _food_name(don))
            add_cell(row, don.description)
            add_cell(row, 'Ja' if don.needs_refrigeration else 'Nein')
            sheet.addElement(row)

        doc.spreadsheet.addElement(sheet)

    if not food_types:
        doc.spreadsheet.addElement(Table(name='Essensspenden'))

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    filename = f'essensspenden_{g.instance.slug}_{date.today()}.ods'
    return send_file(buf, mimetype='application/vnd.oasis.opendocument.spreadsheet',
                     as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# ODS – Alle Anmeldungen (Legacy)
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
        s.addElement(TableCellProperties(backgroundcolor='#a51f2c'))
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

    shifts = db.session.scalars(
        select(Shift)
        .join(Stand, Stand.id == Shift.stand_id)
        .filter(Stand.instance_id == g.instance.id)
        .order_by(Shift.event_date_id, Stand.sort_order)
    ).all()

    for shift in shifts:
        for reg in shift.registrations:
            v = reg.volunteer
            row = TableRow()
            add_cell(row, shift.stand.name)
            add_cell(row, shift.event_date.formatted)
            add_cell(row, shift.time_range)
            add_cell(row, _vol_name(reg))
            add_cell(row, v.email or '' if v else '')
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
# PDF – Dienste (Stundenplan-Stil: je Tag Tabelle mit Stand × Helfer)
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/pdf/dienste', methods=['GET'])
@require_staff
def export_pdf_dienste(slug):
    try:
        from weasyprint import HTML
    except ImportError:
        return error('WeasyPrint nicht installiert', 500)

    color = _primary_color()
    brand = _pdf_branding()
    days = _dienste_by_day(g.instance.id)
    html_content = _build_dienste_pdf_html(days, color, brand, g.instance.name)
    buf = io.BytesIO()
    HTML(string=html_content).write_pdf(buf)
    buf.seek(0)
    filename = f'dienste_{g.instance.slug}_{date.today()}.pdf'
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)


@admin_bp.route('/<slug>/export/pdf/dienste', methods=['POST'])
@require_staff
def export_pdf_dienste_post(slug):
    """POST-Variante: date_ids-Filterung + optionaler E-Mail-Versand."""
    try:
        from weasyprint import HTML
    except ImportError:
        return error('WeasyPrint nicht installiert', 500)

    body = request.get_json() or {}
    date_ids = body.get('date_ids') or []
    email = (body.get('email') or '').strip() or None

    if not date_ids:
        return error('Keine Termine ausgewählt', 422)

    color = _primary_color()
    brand = _pdf_branding()
    days = _dienste_by_day(g.instance.id, date_ids=date_ids)
    html_content = _build_dienste_pdf_html(days, color, brand, g.instance.name)
    buf = io.BytesIO()
    HTML(string=html_content).write_pdf(buf)
    buf.seek(0)
    filename = f'dienste_{g.instance.slug}_{date.today()}.pdf'
    pdf_bytes = buf.read()

    event_dates_for_mail = db.session.scalars(
        select(EventDate).filter(EventDate.id.in_(date_ids)).order_by(EventDate.date)
    ).all()
    date_summaries = [_date_summary(ed) for ed in event_dates_for_mail]
    sender = _sender_name(g.current_user)
    frontend_url = current_app.config.get('FRONTEND_URL', '')

    if email:
        from ...utils.mail import is_mail_configured, send_mail, build_export_email
        if not is_mail_configured(current_app):
            return error('E-Mail nicht konfiguriert', 503)
        subject, html_body = build_export_email(
            instance_name=g.instance.name,
            export_type='Dienstplan',
            sender_name=sender,
            date_summaries=date_summaries,
            base_url=frontend_url,
            instance_slug=g.instance.slug,
        )
        send_mail(
            to=email,
            subject=subject,
            html=html_body,
            attachments=[(filename, 'application/pdf', pdf_bytes)],
        )
        return ok(message=f'PDF an {email} gesendet')

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


# ---------------------------------------------------------------------------
# PDF – Essensspenden (je Spendenart eine Seite, ohne E-Mail)
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/pdf/essen', methods=['GET'])
@require_staff
def export_pdf_essen(slug):
    try:
        from weasyprint import HTML
    except ImportError:
        return error('WeasyPrint nicht installiert', 500)

    tz_name = 'Europe/Berlin'
    try:
        from ...utils.settings_cache import get_global_settings
        gs = get_global_settings()
        if gs and gs.timezone:
            tz_name = gs.timezone
    except Exception:
        pass
    tz = pytz.timezone(tz_name)

    color = _primary_color()
    brand = _pdf_branding()
    food_types = db.session.scalars(
        select(FoodDonationType)
        .filter_by(instance_id=g.instance.id)
        .order_by(FoodDonationType.event_date_id, FoodDonationType.name)
    ).all()
    html_content = _build_essen_pdf_html(food_types, color, brand, g.instance.name, tz)
    buf = io.BytesIO()
    HTML(string=html_content).write_pdf(buf)
    buf.seek(0)
    filename = f'essensspenden_{g.instance.slug}_{date.today()}.pdf'
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)


@admin_bp.route('/<slug>/export/pdf/essen', methods=['POST'])
@require_staff
def export_pdf_essen_post(slug):
    """POST-Variante: date_ids-Filterung + optionaler E-Mail-Versand."""
    try:
        from weasyprint import HTML
    except ImportError:
        return error('WeasyPrint nicht installiert', 500)

    body = request.get_json() or {}
    date_ids = body.get('date_ids') or []
    email = (body.get('email') or '').strip() or None

    if not date_ids:
        return error('Keine Termine ausgewählt', 422)

    tz_name = 'Europe/Berlin'
    try:
        from ...utils.settings_cache import get_global_settings
        gs = get_global_settings()
        if gs and gs.timezone:
            tz_name = gs.timezone
    except Exception:
        pass
    tz = pytz.timezone(tz_name)

    color = _primary_color()
    brand = _pdf_branding()
    food_types = db.session.scalars(
        select(FoodDonationType)
        .filter_by(instance_id=g.instance.id)
        .filter(FoodDonationType.event_date_id.in_(date_ids))
        .order_by(FoodDonationType.event_date_id, FoodDonationType.name)
    ).all()
    html_content = _build_essen_pdf_html(food_types, color, brand, g.instance.name, tz)
    buf = io.BytesIO()
    HTML(string=html_content).write_pdf(buf)
    buf.seek(0)
    filename = f'essensspenden_{g.instance.slug}_{date.today()}.pdf'
    pdf_bytes = buf.read()

    event_dates_for_mail = db.session.scalars(
        select(EventDate).filter(EventDate.id.in_(date_ids)).order_by(EventDate.date)
    ).all()
    date_summaries = [_date_summary(ed) for ed in event_dates_for_mail]
    sender = _sender_name(g.current_user)
    frontend_url = current_app.config.get('FRONTEND_URL', '')

    if email:
        from ...utils.mail import is_mail_configured, send_mail, build_export_email
        if not is_mail_configured(current_app):
            return error('E-Mail nicht konfiguriert', 503)
        subject, html_body = build_export_email(
            instance_name=g.instance.name,
            export_type='Essensspenden',
            sender_name=sender,
            date_summaries=date_summaries,
            base_url=frontend_url,
            instance_slug=g.instance.slug,
        )
        send_mail(
            to=email,
            subject=subject,
            html=html_body,
            attachments=[(filename, 'application/pdf', pdf_bytes)],
        )
        return ok(message=f'PDF an {email} gesendet')

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


# ---------------------------------------------------------------------------
# PDF – Alle Anmeldungen (Legacy)
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/pdf', methods=['GET'])
@require_staff
def export_pdf(slug):
    try:
        from weasyprint import HTML
    except ImportError:
        return error('WeasyPrint nicht installiert', 500)

    shifts = db.session.scalars(
        select(Shift)
        .join(Stand, Stand.id == Shift.stand_id)
        .filter(Stand.instance_id == g.instance.id)
        .order_by(Shift.event_date_id, Stand.sort_order)
    ).all()

    rows_html = ''
    for shift in shifts:
        regs = list(shift.registrations)
        if not regs:
            rows_html += _pdf_row(shift.stand.name, shift.event_date.formatted,
                                   shift.time_range, '—', '')
        for reg in regs:
            v = reg.volunteer
            rows_html += _pdf_row(shift.stand.name, shift.event_date.formatted,
                                   shift.time_range, _vol_name(reg),
                                   v.email or '' if v else '')

    color = _primary_color()
    brand = _pdf_branding()
    html_content = f'''
    <html><head><style>
      body {{ font-family: Arial, sans-serif; font-size: 10pt; margin: 1.5cm; }}
      h1 {{ color: {color}; }}
      table {{ width: 100%; border-collapse: collapse; }}
      th {{ background: {color}; color: white; padding: 6px; text-align: left; }}
      td {{ padding: 5px; border-bottom: 1px solid #eee; }}
      tr:nth-child(even) td {{ background: #f9f9f9; }}
      {brand['css']}
    </style></head><body>
      {brand['html']}
      <h1>Dienstplan – {g.instance.name}</h1>
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
# iCal – Dienste
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/export/ical', methods=['GET'])
@require_staff
def export_ical(slug):
    cal = Calendar()
    cal.add('prodid', f'-//Standdienst//{g.instance.slug}//DE')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', f'Dienstplan {g.instance.name}')

    tz = pytz.timezone('Europe/Berlin')

    shifts = db.session.scalars(
        select(Shift)
        .join(Stand, Stand.id == Shift.stand_id)
        .filter(Stand.instance_id == g.instance.id)
    ).all()

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
