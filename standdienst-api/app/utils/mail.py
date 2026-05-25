import time
import logging

from flask import current_app
from flask_mail import Message
from ..extensions import mail

log = logging.getLogger(__name__)


def is_mail_configured(app=None) -> bool:
    """True wenn SMTP-Server konfiguriert (env oder DB)."""
    cfg = (app or current_app).config
    if cfg.get('MAIL_SERVER'):
        return True
    try:
        from ..models import MailSettings
        ms = MailSettings.query.first()
        return bool(ms and ms.mail_server)
    except Exception:
        return False


def apply_db_mail_config(settings) -> None:
    """Schreibt DB-MailSettings in die Flask-App-Config (aktiviert Flask-Mail)."""
    from ..extensions import mail
    current_app.config.update(
        MAIL_SERVER=settings.mail_server or '',
        MAIL_PORT=settings.mail_port or 587,
        MAIL_USE_TLS=settings.mail_use_tls,
        MAIL_USERNAME=settings.mail_username or '',
        MAIL_PASSWORD=settings.mail_password or '',
        MAIL_DEFAULT_SENDER=settings.mail_default_sender or '',
    )
    mail.init_app(current_app)


def _html_to_text(html: str) -> str:
    """Einfache HTML → Plain-Text Konvertierung für E-Mail-Fallback."""
    import re
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'</?(p|div|tr|h[1-6])[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<td[^>]*>', '  ', text, flags=re.IGNORECASE)
    text = re.sub(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
                  r'\2 (\1)', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def send_mail(to: str, subject: str, html: str, sender_name: str = None,
              retries: int = 3, plain_text: str = None):
    """Sendet eine E-Mail (HTML + Plain-Text) mit bis zu `retries` Versuchen."""
    default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', '')
    sender = f'{sender_name} <{default_sender}>' if sender_name else default_sender
    body = plain_text or _html_to_text(html)
    msg = Message(subject=subject, recipients=[to], html=html, body=body, sender=sender)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            mail.send(msg)
            return
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = 2 ** attempt  # 1s, 2s
                log.warning('E-Mail-Versand fehlgeschlagen (Versuch %d/%d): %s – Retry in %ds',
                            attempt + 1, retries, exc, delay)
                if not current_app.config.get('TESTING'):
                    time.sleep(delay)
    raise last_exc


# ---------------------------------------------------------------------------
# HTML-E-Mail-Template (Basis für alle ausgehenden Mails)
# ---------------------------------------------------------------------------

def build_email_template(
    content_html: str,
    *,
    title: str,
    base_url: str,
    slug: str = None,
    primary_color: str = '#4f46e5',
    logo_url: str = None,
    copyright_text: str = None,
    opt_out_url: str = None,
    opt_out_label: str = 'Benachrichtigungen deaktivieren',
) -> str:
    """Bettet content_html in ein vollständiges, responsives HTML-E-Mail-Template ein."""

    logo_block = ''
    _is_public_url = (
        logo_url
        and logo_url.startswith(('http://', 'https://'))
        and 'localhost' not in logo_url
        and '127.0.0.1' not in logo_url
    )
    if _is_public_url:
        logo_block = (
            f'<div style="margin-bottom:12px;">'
            f'<img src="{logo_url}" alt="{title}" width="180" height="48" '
            f'style="max-height:48px;max-width:180px;object-fit:contain;display:block;margin:0 auto;">'
            f'</div>'
        )

    datenschutz_url = None
    if slug:
        impressum_url = f'{base_url}/{slug}/impressum'
        datenschutz_url = f'{base_url}/{slug}/datenschutz'
        links_block = (
            f'<p style="margin:0 0 10px;">'
            f'<a href="{impressum_url}" style="color:#6b7280;font-size:12px;'
            f'text-decoration:underline;">Impressum</a>'
            f'&nbsp;&nbsp;·&nbsp;&nbsp;'
            f'<a href="{datenschutz_url}" style="color:#6b7280;font-size:12px;'
            f'text-decoration:underline;">Datenschutz</a>'
            f'</p>'
        )
    else:
        links_block = ''

    opt_out_block = ''
    if opt_out_url:
        opt_out_block = (
            f'<p style="margin:8px 0 0;">'
            f'<a href="{opt_out_url}" style="color:#9ca3af;font-size:11px;'
            f'text-decoration:underline;">{opt_out_label}</a>'
            f'</p>'
        )

    datenschutz_info = ''
    if datenschutz_url:
        datenschutz_info = (
            f'<br>Informationen zur Verarbeitung Ihrer Daten finden Sie in unserer '
            f'<a href="{datenschutz_url}" style="color:#9ca3af;text-decoration:underline;">'
            f'Datenschutzerklärung</a>.'
        )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background-color:#f3f4f6;padding:32px 16px;">
    <tr>
      <td align="center">
        <table style="max-width:560px;width:100%;" cellpadding="0" cellspacing="0" role="presentation">

          <!-- Header -->
          <tr>
            <td style="background-color:{primary_color};border-radius:12px 12px 0 0;
                       padding:28px 32px;text-align:center;">
              {logo_block}
              <p style="margin:0;font-size:20px;font-weight:700;color:#ffffff;
                         letter-spacing:-0.3px;">{title}</p>
            </td>
          </tr>

          <!-- Inhalt -->
          <tr>
            <td style="background-color:#ffffff;padding:32px 32px 28px;
                       border-left:1px solid #e5e7eb;border-right:1px solid #e5e7eb;">
              <div style="color:#374151;font-size:15px;line-height:1.7;">
                {content_html}
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f9fafb;border:1px solid #e5e7eb;border-top:none;
                       border-radius:0 0 12px 12px;padding:20px 32px;text-align:center;">
              {links_block}
              <p style="margin:0;color:#9ca3af;font-size:11px;line-height:1.6;">
                Diese E-Mail wurde automatisch versandt.{datenschutz_info}
              </p>
              {opt_out_block}
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# E-Mail-Builder
# ---------------------------------------------------------------------------

def build_welcome_email(
    name: str,
    instance_title: str,
    setup_url: str,
    base_url: str,
    primary_color: str = '#4f46e5',
    logo_url: str = None,
    slug: str = None,
    copyright_text: str = None,
) -> str:
    content = f"""
    <p style="margin:0 0 16px;">Hallo <strong>{name}</strong>,</p>
    <p style="margin:0 0 16px;">
      du hast dich bei <strong>{instance_title}</strong> als Helfer registriert.
    </p>
    <p style="margin:0 0 28px;">
      Bitte klicke auf den folgenden Button, um dein Passwort einzurichten
      und dein Konto zu aktivieren:
    </p>
    <p style="margin:0 0 28px;text-align:center;">
      <a href="{setup_url}"
         style="background:{primary_color};color:#ffffff;padding:13px 30px;
                border-radius:8px;text-decoration:none;font-weight:600;
                font-size:15px;display:inline-block;">
        Passwort einrichten
      </a>
    </p>
    <p style="margin:0;color:#6b7280;font-size:13px;">
      Der Link ist <strong>7 Tage</strong> gültig.
      Falls du keine Registrierung angefordert hast, kannst du diese E-Mail ignorieren.
    </p>
    """
    return build_email_template(
        content,
        title=instance_title,
        base_url=base_url,
        slug=slug,
        primary_color=primary_color,
        logo_url=logo_url,
        copyright_text=copyright_text,
    )


def build_reset_email(
    name: str,
    reset_url: str,
    base_url: str,
    *,
    title: str = 'Standdienst',
    slug: str = None,
    primary_color: str = '#4f46e5',
    logo_url: str = None,
    copyright_text: str = None,
) -> str:
    content = f"""
    <p style="margin:0 0 16px;">Hallo <strong>{name}</strong>,</p>
    <p style="margin:0 0 28px;">
      du hast eine Passwort-Zurücksetzung angefordert.
      Klicke auf den folgenden Button, um ein neues Passwort zu setzen:
    </p>
    <p style="margin:0 0 28px;text-align:center;">
      <a href="{reset_url}"
         style="background:{primary_color};color:#ffffff;padding:13px 30px;
                border-radius:8px;text-decoration:none;font-weight:600;
                font-size:15px;display:inline-block;">
        Passwort zurücksetzen
      </a>
    </p>
    <p style="margin:0;color:#6b7280;font-size:13px;">
      Der Link ist <strong>1 Stunde</strong> gültig.
      Falls du keine Zurücksetzung angefordert hast, kannst du diese E-Mail ignorieren.
    </p>
    """
    return build_email_template(
        content,
        title=title,
        base_url=base_url,
        slug=slug,
        primary_color=primary_color,
        logo_url=logo_url,
        copyright_text=copyright_text,
    )


def build_registration_email(
    name: str,
    instance_title: str,
    login_url: str,
    base_url: str = '',
    slug: str = None,
    primary_color: str = '#4f46e5',
    logo_url: str = None,
    copyright_text: str = None,
) -> str:
    content = f"""
    <p style="margin:0 0 16px;">Hallo <strong>{name}</strong>,</p>
    <p style="margin:0 0 28px;">
      deine Registrierung bei <strong>{instance_title}</strong> war erfolgreich.
    </p>
    <p style="margin:0 0 28px;text-align:center;">
      <a href="{login_url}"
         style="background:{primary_color};color:#ffffff;padding:13px 30px;
                border-radius:8px;text-decoration:none;font-weight:600;
                font-size:15px;display:inline-block;">
        Zum Login
      </a>
    </p>
    """
    return build_email_template(
        content,
        title=instance_title,
        base_url=base_url,
        slug=slug,
        primary_color=primary_color,
        logo_url=logo_url,
        copyright_text=copyright_text,
    )


def build_invite_email(
    name: str,
    role_label: str,
    login_url: str,
    base_url: str,
    primary_color: str = '#4f46e5',
) -> str:
    """Einladungsmail wenn ein Passwort bereits gesetzt wurde (nur noch für Admin-Anlegen)."""
    content = f"""
    <p style="margin:0 0 16px;">Hallo <strong>{name}</strong>,</p>
    <p style="margin:0 0 16px;">
      ein Admin-Konto mit der Rolle <strong>{role_label}</strong> wurde für dich angelegt.
    </p>
    <p style="margin:0 0 28px;">
      Du kannst dich jetzt mit deiner E-Mail-Adresse und dem dir mitgeteilten Passwort anmelden:
    </p>
    <p style="margin:0 0 28px;text-align:center;">
      <a href="{login_url}"
         style="background:{primary_color};color:#ffffff;padding:13px 30px;
                border-radius:8px;text-decoration:none;font-weight:600;
                font-size:15px;display:inline-block;">
        Zum Login
      </a>
    </p>
    <p style="margin:0;color:#6b7280;font-size:13px;">
      Falls du diese E-Mail irrtümlich erhalten hast, kannst du sie ignorieren.
    </p>
    """
    return build_email_template(
        content,
        title='Standdienst',
        base_url=base_url,
        primary_color=primary_color,
    )


def build_organizer_invite_email(
    name: str,
    setup_url: str,
    instances: list,
    base_url: str,
    primary_color: str = '#4f46e5',
) -> str:
    """Einladungsmail für neue Organisatoren ohne Passwort.

    instances: [{'name': str, 'volunteer_url': str}]
    """
    cell = 'style="padding:8px 12px;font-size:13px;border-bottom:1px solid #f3f4f6;"'
    head = ('style="padding:8px 12px;background-color:#f9fafb;font-size:12px;font-weight:600;'
            'color:#6b7280;text-transform:uppercase;letter-spacing:.04em;'
            'border-bottom:2px solid #e5e7eb;text-align:left;"')

    instance_section = ''
    if instances:
        rows = ''.join(
            f'<tr>'
            f'<td {cell}>{inst["name"]}</td>'
            f'<td {cell}><a href="{inst["volunteer_url"]}" '
            f'style="color:{primary_color};word-break:break-all;">'
            f'{inst["volunteer_url"]}</a></td>'
            f'</tr>'
            for inst in instances
        )
        instance_section = (
            f'<h3 style="margin:24px 0 10px;font-size:14px;font-weight:600;color:#111827;">'
            f'Deine Instanzen</h3>'
            f'<table width="100%" cellpadding="0" cellspacing="0"'
            f' style="border:1px solid #e5e7eb;border-radius:8px;border-collapse:collapse;">'
            f'<tr><th {head}>Instanz</th><th {head}>Helfer-URL</th></tr>'
            f'{rows}'
            f'</table>'
            f'<p style="margin:8px 0 0;color:#6b7280;font-size:12px;">'
            f'Diese URLs können Helfern mitgeteilt werden, um sich anzumelden.</p>'
        )

    content = f"""
    <p style="margin:0 0 16px;">Hallo <strong>{name}</strong>,</p>
    <p style="margin:0 0 16px;">
      ein Organisator-Konto bei Standdienst wurde für dich angelegt.
    </p>
    <p style="margin:0 0 28px;">
      Bitte klicke auf den folgenden Button, um dein Passwort einzurichten
      und dein Konto zu aktivieren:
    </p>
    <p style="margin:0 0 28px;text-align:center;">
      <a href="{setup_url}"
         style="background:{primary_color};color:#ffffff;padding:13px 30px;
                border-radius:8px;text-decoration:none;font-weight:600;
                font-size:15px;display:inline-block;">
        Passwort einrichten
      </a>
    </p>
    <p style="margin:0 0 0;color:#6b7280;font-size:13px;">
      Der Link ist <strong>7 Tage</strong> gültig.
      Falls du diese E-Mail irrtümlich erhalten hast, kannst du sie ignorieren.
    </p>
    {instance_section}
    """
    return build_email_template(
        content,
        title='Standdienst',
        base_url=base_url,
        primary_color=primary_color,
    )


def build_shift_confirmation_email(
    name: str,
    instance_title: str,
    stand: str,
    date: str,
    time_range: str,
    my_shifts_url: str,
    base_url: str,
    slug: str = None,
    primary_color: str = '#4f46e5',
    logo_url: str = None,
    copyright_text: str = None,
    opt_out_url: str = None,
) -> str:
    """Bestätigungsmail nach erfolgreicher Schicht-Anmeldung."""
    content = f"""
    <p style="margin:0 0 16px;">Hallo <strong>{name}</strong>,</p>
    <p style="margin:0 0 16px;">
      deine Anmeldung bei <strong>{instance_title}</strong> war erfolgreich.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid #e5e7eb;border-radius:8px;border-collapse:collapse;
                  margin-bottom:24px;">
      <tr>
        <td style="padding:8px 12px;font-size:13px;color:#6b7280;
                   border-bottom:1px solid #e5e7eb;width:40%;">Ort</td>
        <td style="padding:8px 12px;font-size:13px;color:#374151;
                   border-bottom:1px solid #e5e7eb;">{stand}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;font-size:13px;color:#6b7280;
                   border-bottom:1px solid #e5e7eb;">Datum</td>
        <td style="padding:8px 12px;font-size:13px;color:#374151;
                   border-bottom:1px solid #e5e7eb;">{date}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;font-size:13px;color:#6b7280;">Zeit</td>
        <td style="padding:8px 12px;font-size:13px;color:#374151;">{time_range}</td>
      </tr>
    </table>
    <p style="margin:0 0 24px;text-align:center;">
      <a href="{my_shifts_url}"
         style="background:{primary_color};color:#ffffff;padding:13px 30px;
                border-radius:8px;text-decoration:none;font-weight:600;
                font-size:15px;display:inline-block;">
        Meine Anmeldungen ansehen
      </a>
    </p>
    """
    return build_email_template(
        content,
        title=instance_title,
        base_url=base_url,
        slug=slug,
        primary_color=primary_color,
        logo_url=logo_url,
        copyright_text=copyright_text,
        opt_out_url=opt_out_url,
        opt_out_label='Bestätigungsmails deaktivieren',
    )


def build_daten_auskunft_email(
    name: str,
    data: dict,
    instance_title: str,
    base_url: str,
    slug: str = None,
    primary_color: str = '#4f46e5',
    logo_url: str = None,
    copyright_text: str = None,
) -> str:
    v = data['volunteer']
    regs = data['registrations']
    food = data['food_donations']

    cell = ('style="padding:8px 12px;border-bottom:1px solid #e5e7eb;'
            'font-size:13px;color:#374151;"')
    head = ('style="padding:8px 12px;background-color:#f9fafb;font-size:12px;'
            'font-weight:600;color:#6b7280;text-transform:uppercase;'
            'letter-spacing:.04em;border-bottom:2px solid #e5e7eb;"')
    table_attrs = ('width="100%" cellpadding="0" cellspacing="0" '
                   'style="border:1px solid #e5e7eb;border-radius:8px;'
                   'border-collapse:collapse;overflow:hidden;"')

    reg_rows = ''.join(
        f'<tr><td {cell}>{r["date"]}</td>'
        f'<td {cell}>{r["stand"]}</td>'
        f'<td {cell}>{r["start_time"]}–{r["end_time"]}</td></tr>'
        for r in regs
    )
    food_rows = ''.join(
        f'<tr><td {cell}>{f["food_type"]}</td>'
        f'<td {cell}>{f["description"]}</td>'
        f'<td {cell}>{"Ja" if f["needs_refrigeration"] else "Nein"}</td></tr>'
        for f in food
    )

    reg_table = (
        f'<table {table_attrs}>'
        f'<tr><th {head}>Datum</th><th {head}>Ort</th><th {head}>Zeit</th></tr>'
        f'{reg_rows}</table>'
    ) if regs else (
        '<p style="color:#9ca3af;font-size:13px;font-style:italic;margin:0;">'
        'Keine Einträge</p>'
    )
    food_table = (
        f'<table {table_attrs}>'
        f'<tr><th {head}>Kategorie</th><th {head}>Beschreibung</th>'
        f'<th {head}>Kühlung</th></tr>'
        f'{food_rows}</table>'
    ) if food else (
        '<p style="color:#9ca3af;font-size:13px;font-style:italic;margin:0;">'
        'Keine Einträge</p>'
    )

    content = f"""
    <p style="margin:0 0 16px;">Hallo <strong>{name}</strong>,</p>
    <p style="margin:0 0 24px;">
      gemäß <strong>Art. 15 DSGVO</strong> erhalten Sie eine Übersicht aller bei
      <strong>{instance_title}</strong> gespeicherten Daten.
    </p>
    <h3 style="margin:0 0 10px;font-size:14px;font-weight:600;color:#111827;">
      Personenbezogene Daten
    </h3>
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid #e5e7eb;border-radius:8px;border-collapse:collapse;
                  margin-bottom:24px;">
      <tr>
        <td style="padding:8px 12px;font-size:13px;color:#6b7280;
                   border-bottom:1px solid #e5e7eb;width:40%;">Name</td>
        <td style="padding:8px 12px;font-size:13px;color:#374151;
                   border-bottom:1px solid #e5e7eb;">{v["name"]}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;font-size:13px;color:#6b7280;
                   border-bottom:1px solid #e5e7eb;">E-Mail</td>
        <td style="padding:8px 12px;font-size:13px;color:#374151;
                   border-bottom:1px solid #e5e7eb;">{v["email"] or "–"}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;font-size:13px;color:#6b7280;
                   border-bottom:1px solid #e5e7eb;">Registriert am</td>
        <td style="padding:8px 12px;font-size:13px;color:#374151;
                   border-bottom:1px solid #e5e7eb;">{v["created_at"] or "–"}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;font-size:13px;color:#6b7280;">
          Einwilligung erteilt am</td>
        <td style="padding:8px 12px;font-size:13px;color:#374151;">
          {v["consent_given_at"] or "–"}</td>
      </tr>
    </table>
    <h3 style="margin:0 0 10px;font-size:14px;font-weight:600;color:#111827;">
      Dienstanmeldungen ({len(regs)})
    </h3>
    <div style="margin-bottom:24px;">{reg_table}</div>
    <h3 style="margin:0 0 10px;font-size:14px;font-weight:600;color:#111827;">
      Essensspenden ({len(food)})
    </h3>
    <div>{food_table}</div>
    """
    return build_email_template(
        content,
        title=instance_title,
        base_url=base_url,
        slug=slug,
        primary_color=primary_color,
        logo_url=logo_url,
        copyright_text=copyright_text,
    )


def build_reminder_email(
    name: str,
    shifts: list,
    food_items: list,
    instance_title: str,
    base_url: str,
    slug: str = None,
    primary_color: str = '#4f46e5',
    logo_url: str = None,
    copyright_text: str = None,
    opt_out_url: str = None,
) -> str:
    """Erinnerungsmail: morgen anstehende Dienste und/oder Essensspenden."""

    cell = ('style="padding:8px 12px;border-bottom:1px solid #e5e7eb;'
            'font-size:13px;color:#374151;"')
    head = ('style="padding:8px 12px;background-color:#f9fafb;font-size:12px;'
            'font-weight:600;color:#6b7280;text-transform:uppercase;'
            'letter-spacing:.04em;border-bottom:2px solid #e5e7eb;"')
    table_attrs = ('width="100%" cellpadding="0" cellspacing="0" '
                   'style="border:1px solid #e5e7eb;border-radius:8px;'
                   'border-collapse:collapse;overflow:hidden;margin-bottom:24px;"')

    sections = ''

    if shifts:
        rows = ''.join(
            f'<tr><td {cell}>{s["stand"]}</td><td {cell}>{s["time"]}</td></tr>'
            for s in shifts
        )
        sections += (
            f'<h3 style="margin:0 0 10px;font-size:14px;font-weight:600;color:#111827;">'
            f'Dienste morgen</h3>'
            f'<table {table_attrs}>'
            f'<tr><th {head}>Ort</th><th {head}>Zeit</th></tr>'
            f'{rows}</table>'
        )

    if food_items:
        rows = ''.join(
            f'<tr><td {cell}>{f["name"]}</td>'
            f'<td {cell}>{f["description"]}</td>'
            f'<td {cell}>{f["delivery_time"] or "–"}{(" · " + f["delivery_location"]) if f.get("delivery_location") else ""}</td></tr>'
            for f in food_items
        )
        sections += (
            f'<h3 style="margin:0 0 10px;font-size:14px;font-weight:600;color:#111827;">'
            f'Essensspenden morgen</h3>'
            f'<table {table_attrs}>'
            f'<tr><th {head}>Kategorie</th><th {head}>Was du mitbringst</th><th {head}>Abgabe</th></tr>'
            f'{rows}</table>'
        )

    login_url = f'{base_url}/{slug}' if slug else base_url
    content = f"""
    <p style="margin:0 0 16px;">Hallo <strong>{name}</strong>,</p>
    <p style="margin:0 0 24px;">
      das ist deine Erinnerung für morgen bei <strong>{instance_title}</strong>:
    </p>
    {sections}
    <p style="margin:0;text-align:center;">
      <a href="{login_url}"
         style="background:{primary_color};color:#ffffff;padding:13px 30px;
                border-radius:8px;text-decoration:none;font-weight:600;
                font-size:15px;display:inline-block;">
        Zur Übersicht
      </a>
    </p>
    """
    return build_email_template(
        content,
        title=instance_title,
        base_url=base_url,
        slug=slug,
        primary_color=primary_color,
        logo_url=logo_url,
        copyright_text=copyright_text,
        opt_out_url=opt_out_url,
        opt_out_label='Erinnerungsmails deaktivieren',
    )


def build_organizer_digest_email(
    organizer_name: str,
    instance_title: str,
    date_label: str,
    registrations: list,
    cancellations: list,
    food_donations: list,
    base_url: str,
    slug: str,
    primary_color: str = '#4f46e5',
    logo_url: str = None,
    copyright_text: str = None,
    opt_out_url: str = None,
) -> str:
    """Tägliche Zusammenfassung der Aktivitäten für Organisatoren."""

    def _table_section(title, rows, headers, row_fn):
        if not rows:
            return ''
        td_style = 'padding:8px 12px;border-bottom:1px solid #eee;'
        def _row(r):
            cells = ''.join(f'<td style="{td_style}">{c}</td>' for c in row_fn(r))
            return f'<tr>{cells}</tr>'
        row_html = ''.join(_row(r) for r in rows)
        head_html = ''.join(f'<th style="padding:8px 12px;text-align:left;background:#f4f4f5;font-size:12px;color:#71717a;">{h}</th>' for h in headers)
        return (
            f'<p style="margin:24px 0 8px;font-weight:600;color:#18181b;">{title}</p>'
            f'<table style="width:100%;border-collapse:collapse;font-size:14px;border:1px solid #eee;border-radius:8px;overflow:hidden;">'
            f'<thead><tr>{head_html}</tr></thead>'
            f'<tbody>{row_html}</tbody></table>'
        )

    reg_section = _table_section(
        f'Neue Anmeldungen ({len(registrations)})',
        registrations,
        ['Name', 'Stand', 'Zeit'],
        lambda r: [r['name'], r['stand'], r['time']],
    )
    cancel_section = _table_section(
        f'Abmeldungen ({len(cancellations)})',
        cancellations,
        ['Name', 'Stand', 'Zeit'],
        lambda r: [r['name'], r['stand'], r['time']],
    )
    food_section = _table_section(
        f'Essensspenden ({len(food_donations)})',
        food_donations,
        ['Von', 'Kategorie', 'Beschreibung'],
        lambda r: [r['name'], r['food_type'], r['description'] or '—'],
    )

    admin_url = f'{base_url}/admin/{slug}/registrations'
    content = f"""
    <p style="margin:0 0 16px;">Hallo <strong>{organizer_name}</strong>,</p>
    <p style="margin:0 0 24px;">
      hier ist deine Zusammenfassung für <strong>{instance_title}</strong> vom <strong>{date_label}</strong>:
    </p>
    {reg_section or '<p style="color:#71717a;">Keine neuen Anmeldungen.</p>' if not cancel_section and not food_section else reg_section}
    {cancel_section}
    {food_section}
    <p style="margin:24px 0 0;text-align:center;">
      <a href="{admin_url}"
         style="background:{primary_color};color:#ffffff;padding:13px 30px;
                border-radius:8px;text-decoration:none;font-weight:600;
                font-size:15px;display:inline-block;">
        Zur Anmeldungsübersicht
      </a>
    </p>
    """
    return build_email_template(
        content,
        title=instance_title,
        base_url=base_url,
        slug=slug,
        primary_color=primary_color,
        logo_url=logo_url,
        copyright_text=copyright_text,
        opt_out_url=opt_out_url,
        opt_out_label='Tägliche Zusammenfassung deaktivieren',
    )
