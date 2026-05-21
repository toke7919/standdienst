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


def send_mail(to: str, subject: str, html: str, sender_name: str = None, retries: int = 3):
    """Sendet eine E-Mail mit bis zu `retries` Versuchen (exponentielles Backoff)."""
    default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', '')
    sender = f'{sender_name} <{default_sender}>' if sender_name else default_sender
    msg = Message(subject=subject, recipients=[to], html=html, sender=sender)
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
) -> str:
    """Bettet content_html in ein vollständiges, responsives HTML-E-Mail-Template ein."""

    logo_block = ''
    if logo_url:
        logo_block = (
            f'<div style="margin-bottom:12px;">'
            f'<img src="{logo_url}" alt="{title}" '
            f'style="max-height:48px;max-width:180px;object-fit:contain;">'
            f'</div>'
        )

    copyright_block = ''
    if copyright_text:
        copyright_block = (
            f'<p style="margin:0 0 8px;color:#6b7280;font-size:12px;">{copyright_text}</p>'
        )

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
        datenschutz_url = f'{base_url}/datenschutz'
        links_block = ''

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
              {copyright_block}
              {links_block}
              <p style="margin:0;color:#9ca3af;font-size:11px;line-height:1.6;">
                Diese E-Mail wurde automatisch versandt.<br>
                Informationen zur Verarbeitung Ihrer Daten finden Sie in unserer
                <a href="{datenschutz_url}"
                   style="color:#6b7280;text-decoration:underline;">Datenschutzerklärung</a>.
              </p>
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
