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
        from sqlalchemy import select
        from ..extensions import db
        from ..models import MailSettings
        ms = db.session.scalars(select(MailSettings)).first()
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
        MAIL_SENDER_NAME=settings.mail_sender_name or '',
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
              retries: int = 3, plain_text: str = None,
              attachments: list | None = None):
    """Sendet eine E-Mail (HTML + Plain-Text) mit bis zu `retries` Versuchen."""
    default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', '')
    _name = sender_name or current_app.config.get('MAIL_SENDER_NAME', '')
    sender = f'{_name} <{default_sender}>' if _name else default_sender
    body = plain_text or _html_to_text(html)
    msg = Message(subject=subject, recipients=[to], html=html, body=body, sender=sender)
    if attachments:
        for filename, content_type, data in attachments:
            msg.attach(filename, content_type, data)
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

_DEFAULT_PRIMARY = '#a51f2c'   # Karmin – neues Brand-Farbschema
_BG_OUTER   = '#f5ece1'        # Papier
_BG_CONTENT = '#fdf6e9'        # Soft cream
_BG_FOOTER  = '#e9d8bd'        # Sand warm
_BORDER     = '#dbc8a8'        # Sand
_TEXT_MAIN  = '#1a1311'        # Tinte
_TEXT_MUTED = '#7a695a'        # Muted


def get_logo_for_email(logo_filename: str, base_url: str) -> str | None:
    """Liefert ein Base64-Data-URI des Logos (bevorzugt) oder die /uploads/-URL als Fallback."""
    if not logo_filename:
        return None
    try:
        import base64, mimetypes, os
        from flask import current_app
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        path = os.path.join(upload_folder, logo_filename)
        if os.path.isfile(path):
            mime, _ = mimetypes.guess_type(path)
            mime = mime or 'image/png'
            with open(path, 'rb') as fh:
                data = base64.b64encode(fh.read()).decode()
            return f'data:{mime};base64,{data}'
    except Exception:
        pass
    return f'{base_url}/uploads/{logo_filename}'


def get_platform_logo_for_email() -> str | None:
    """Liefert das Plattform-Logo (logo-email.png, helle Version für farbige Header) als Base64-Data-URI."""
    try:
        import base64, os
        from flask import current_app
        # static_folder is None (app created with static_folder=None);
        # logo-email.png is the light-on-dark variant for use inside the colored email header
        root = current_app.root_path
        for name in ('logo-email.png', 'logo.png'):
            path = os.path.normpath(os.path.join(root, '..', 'static', 'dist', name))
            if os.path.isfile(path):
                with open(path, 'rb') as fh:
                    data = base64.b64encode(fh.read()).decode()
                return f'data:image/png;base64,{data}'
    except Exception:
        pass
    return None


def get_effective_logo_for_email(logo_filename: str | None, base_url: str) -> str | None:
    """Liefert Instanz-Logo oder – als Fallback – das Plattform-Logo."""
    logo = get_logo_for_email(logo_filename, base_url) if logo_filename else None
    return logo or get_platform_logo_for_email()


def build_email_template(
    content_html: str,
    *,
    title: str,
    base_url: str,
    slug: str = None,
    impressum_url: str = None,
    datenschutz_url: str = None,
    primary_color: str = _DEFAULT_PRIMARY,
    logo_url: str = None,
    copyright_text: str = None,
    opt_out_url: str = None,
    opt_out_label: str = 'Benachrichtigungen deaktivieren',
    show_branding: bool = True,
) -> str:
    """Bettet content_html in ein vollständiges, responsives HTML-E-Mail-Template ein."""

    # Plattform-Logo für den Werbe-Footer (immer die helle Variante auf dunklem Grund)
    _promo_logo = get_platform_logo_for_email() or '' if show_branding else ''
    if _promo_logo:
        _promo_footer = f"""
          <tr>
            <td style="padding:28px 0 4px;text-align:center;">
              <table align="center" style="max-width:400px;width:100%;background-color:#1a1311;
                            border-radius:12px;margin:0 auto;" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td style="padding:28px 32px 24px;text-align:center;">
                    <img src="{_promo_logo}" alt="Standdienst" width="220"
                         style="max-width:220px;height:auto;display:block;margin:0 auto 14px;">
                    <p style="margin:0 0 6px;color:#fdf6e9;font-size:14px;font-weight:700;
                               letter-spacing:-0.2px;line-height:1.4;">
                      Helfer koordinieren – ganz ohne Stress.
                    </p>
                    <p style="margin:0 0 16px;color:#c8b8a2;font-size:12px;line-height:1.6;">
                      Standdienst ist die Plattform f&uuml;r Vereine und<br>
                      Veranstaltungen: Dienste, St&auml;nde und Essensspenden&nbsp;&ndash;<br>
                      einfach, datenschutzkonform, ohne Tracking.
                    </p>
                    <a href="{base_url}"
                       style="display:inline-block;background-color:#a51f2c;color:#fdf6e9;
                              font-size:12px;font-weight:600;text-decoration:none;
                              padding:8px 20px;border-radius:6px;">
                      Mehr erfahren &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>"""
    else:
        _promo_footer = ''

    logo_block = ''
    _renderable = (
        logo_url and (
            logo_url.startswith('data:')
            or (
                logo_url.startswith(('http://', 'https://'))
                and 'localhost' not in logo_url
                and '127.0.0.1' not in logo_url
            )
        )
    )
    if _renderable:
        logo_block = (
            f'<div style="margin-bottom:12px;">'
            f'<img src="{logo_url}" alt="{title}" '
            f'style="max-width:220px;max-height:72px;width:auto;height:auto;display:block;margin:0 auto;">'
            f'</div>'
        )

    # Impressum/Datenschutz-URLs: explizit → Slug-basiert → Plattform-Fallback
    _impressum = (impressum_url
                  or (f'{base_url}/{slug}/impressum' if slug else None)
                  or (f'{base_url}/impressum' if base_url else None))
    _datenschutz = (datenschutz_url
                    or (f'{base_url}/{slug}/datenschutz' if slug else None)
                    or (f'{base_url}/datenschutz' if base_url else None))

    if _impressum or _datenschutz:
        parts = []
        if _impressum:
            parts.append(
                f'<a href="{_impressum}" style="color:{_TEXT_MUTED};font-size:12px;'
                f'text-decoration:underline;">Impressum</a>'
            )
        if _datenschutz:
            parts.append(
                f'<a href="{_datenschutz}" style="color:{_TEXT_MUTED};font-size:12px;'
                f'text-decoration:underline;">Datenschutz</a>'
            )
        links_block = (
            f'<p style="margin:0 0 10px;">'
            + '&nbsp;&nbsp;·&nbsp;&nbsp;'.join(parts)
            + '</p>'
        )
    else:
        links_block = ''

    opt_out_block = ''
    if opt_out_url:
        opt_out_block = (
            f'<p style="margin:8px 0 0;">'
            f'<a href="{opt_out_url}" style="color:{_TEXT_MUTED};font-size:11px;'
            f'text-decoration:underline;">{opt_out_label}</a>'
            f'</p>'
        )

    datenschutz_info = ''
    if _datenschutz:
        datenschutz_info = (
            f'<br>Informationen zur Verarbeitung Ihrer Daten finden Sie in unserer '
            f'<a href="{_datenschutz}" style="color:{_TEXT_MUTED};text-decoration:underline;">'
            f'Datenschutzerklärung</a>.'
        )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:{_BG_OUTER};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background-color:{_BG_OUTER};padding:32px 16px;">
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
            <td style="background-color:{_BG_CONTENT};padding:32px 32px 28px;
                       border-left:1px solid {_BORDER};border-right:1px solid {_BORDER};">
              <div style="color:{_TEXT_MAIN};font-size:15px;line-height:1.7;">
                {content_html}
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:{_BG_FOOTER};border:1px solid {_BORDER};border-top:none;
                       border-radius:0 0 12px 12px;padding:20px 32px;text-align:center;">
              {links_block}
              <p style="margin:0;color:{_TEXT_MUTED};font-size:11px;line-height:1.6;">
                Diese E-Mail wurde automatisch versandt.{datenschutz_info}
              </p>
              {opt_out_block}
            </td>
          </tr>

        </table>
{_promo_footer}
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
    primary_color: str = _DEFAULT_PRIMARY,
    logo_url: str = None,
    slug: str = None,
    copyright_text: str = None,
    show_branding: bool = True,
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
        show_branding=show_branding,
    )


def build_reset_email(
    name: str,
    reset_url: str,
    base_url: str,
    *,
    title: str = 'Standdienst',
    slug: str = None,
    impressum_url: str = None,
    datenschutz_url: str = None,
    primary_color: str = _DEFAULT_PRIMARY,
    logo_url: str = None,
    copyright_text: str = None,
    show_branding: bool = True,
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
        impressum_url=impressum_url,
        datenschutz_url=datenschutz_url,
        primary_color=primary_color,
        logo_url=logo_url,
        copyright_text=copyright_text,
        show_branding=show_branding,
    )


def build_registration_email(
    name: str,
    instance_title: str,
    login_url: str,
    base_url: str = '',
    slug: str = None,
    primary_color: str = _DEFAULT_PRIMARY,
    logo_url: str = None,
    copyright_text: str = None,
    show_branding: bool = True,
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
        show_branding=show_branding,
    )


def build_invite_email(
    name: str,
    role_label: str,
    login_url: str,
    base_url: str,
    primary_color: str = _DEFAULT_PRIMARY,
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
    primary_color: str = _DEFAULT_PRIMARY,
    logo_url: str = None,
    copyright_text: str = None,
    impressum_url: str = None,
    datenschutz_url: str = None,
    show_branding: bool = True,
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
        logo_url=logo_url,
        copyright_text=copyright_text,
        impressum_url=impressum_url,
        datenschutz_url=datenschutz_url,
        show_branding=show_branding,
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
    primary_color: str = _DEFAULT_PRIMARY,
    logo_url: str = None,
    copyright_text: str = None,
    opt_out_url: str = None,
    show_branding: bool = True,
) -> str:
    """Bestätigungsmail nach erfolgreicher Dienst-Anmeldung."""
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
        show_branding=show_branding,
    )


def build_daten_auskunft_email(
    name: str,
    data: dict,
    instance_title: str,
    base_url: str,
    slug: str = None,
    primary_color: str = _DEFAULT_PRIMARY,
    logo_url: str = None,
    copyright_text: str = None,
    show_branding: bool = True,
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

    inst_url = f'{base_url}/{slug}' if slug else base_url
    content = f"""
    <p style="margin:0 0 16px;">Hallo <strong>{name}</strong>,</p>
    <p style="margin:0 0 24px;">
      gemäß <strong>Art. 15 DSGVO</strong> erhalten Sie eine Übersicht aller bei
      <strong>{instance_title}</strong>
      (unter <a href="{inst_url}" style="color:#a51f2c;">{inst_url}</a>)
      gespeicherten Daten.
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
        show_branding=show_branding,
    )


def build_reminder_email(
    name: str,
    shifts: list,
    food_items: list,
    instance_title: str,
    base_url: str,
    slug: str = None,
    primary_color: str = _DEFAULT_PRIMARY,
    logo_url: str = None,
    copyright_text: str = None,
    opt_out_url: str = None,
    show_branding: bool = True,
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
        show_branding=show_branding,
    )


def build_export_email(
    instance_name: str,
    export_type: str,
    sender_name: str | None = None,
    date_summaries: list | None = None,
    base_url: str = '',
    instance_slug: str | None = None,
    logo_url: str | None = None,
    primary_color: str | None = None,
    copyright_text: str | None = None,
) -> tuple[str, str]:
    subject = f'{export_type} – {instance_name}'

    if export_type == 'Essensspenden':
        action = 'die Übersicht der Essensspenden'
    else:
        action = 'den Dienstplan'

    if sender_name:
        intro = f'<p><strong>{sender_name}</strong> sendet dir {action} für folgende Termine:</p>'
    else:
        intro = f'<p>Anbei {action} für folgende Termine:</p>'

    if date_summaries:
        items = ''.join(f'<li style="margin-bottom:2px;">{ds}</li>' for ds in date_summaries)
        dates_block = f'<ul style="margin:6px 0 12px;padding-left:20px;color:#374151;">{items}</ul>'
    else:
        dates_block = ''

    content = f'{intro}\n{dates_block}'

    html = build_email_template(
        content,
        title=f'{export_type} – {instance_name}',
        base_url=base_url,
        slug=instance_slug,
        logo_url=logo_url,
        primary_color=primary_color or _DEFAULT_PRIMARY,
        copyright_text=copyright_text,
    )
    return subject, html


def build_organizer_digest_email(
    organizer_name: str,
    instance_title: str,
    date_label: str,
    registrations: list,
    cancellations: list,
    food_donations: list,
    base_url: str,
    slug: str,
    primary_color: str = _DEFAULT_PRIMARY,
    logo_url: str = None,
    copyright_text: str = None,
    opt_out_url: str = None,
    show_branding: bool = True,
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
        show_branding=show_branding,
    )
