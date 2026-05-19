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


def _footer(base_url: str, datenschutz_path: str = '/datenschutz') -> str:
    return f"""
    <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
    <p style="color:#6b7280;font-size:12px;">
      Diese E-Mail wurde automatisch versandt.<br>
      Informationen zur Verarbeitung Ihrer Daten finden Sie in unserer
      <a href="{base_url}{datenschutz_path}" style="color:#4f46e5;">Datenschutzerklärung</a>.
    </p>
    """


def build_reset_email(name: str, reset_url: str, base_url: str) -> str:
    return f"""
    <p>Hallo {name},</p>
    <p>du hast eine Passwort-Zurücksetzung angefordert.</p>
    <p><a href="{reset_url}">Passwort zurücksetzen</a></p>
    <p>Der Link ist <strong>1 Stunde</strong> gültig.</p>
    <p>Falls du keine Zurücksetzung angefordert hast, kannst du diese E-Mail ignorieren.</p>
    {_footer(base_url)}
    """


def build_registration_email(name: str, instance_title: str, login_url: str,
                              base_url: str = '') -> str:
    return f"""
    <p>Hallo {name},</p>
    <p>deine Registrierung bei <strong>{instance_title}</strong> war erfolgreich.</p>
    <p><a href="{login_url}">Zum Login</a></p>
    {_footer(base_url)}
    """


def build_daten_auskunft_email(name: str, data: dict, instance_title: str, base_url: str) -> str:
    """Art. 15 DSGVO – Datenauskunft als HTML-E-Mail."""
    v = data['volunteer']
    regs = data['registrations']
    food = data['food_donations']

    reg_rows = ''.join(
        f'<tr><td>{r["date"]}</td><td>{r["stand"]}</td>'
        f'<td>{r["start_time"]}–{r["end_time"]}</td></tr>'
        for r in regs
    )
    food_rows = ''.join(
        f'<tr><td>{f["food_type"]}</td><td>{f["description"]}</td>'
        f'<td>{"Ja" if f["needs_refrigeration"] else "Nein"}</td></tr>'
        for f in food
    )

    return f"""
    <p>Hallo {name},</p>
    <p>gemäß <strong>Art. 15 DSGVO</strong> erhalten Sie eine Übersicht aller bei
    <strong>{instance_title}</strong> gespeicherten Daten.</p>
    <h3>Personendaten</h3>
    <ul>
      <li><strong>Name:</strong> {v["name"]}</li>
      <li><strong>E-Mail:</strong> {v["email"] or "–"}</li>
      <li><strong>Registriert am:</strong> {v["created_at"] or "–"}</li>
      <li><strong>Einwilligung erteilt am:</strong> {v["consent_given_at"] or "–"}</li>
    </ul>
    <h3>Schichtanmeldungen ({len(regs)})</h3>
    {'<table border="1" cellpadding="4"><tr><th>Datum</th><th>Ort</th><th>Zeit</th></tr>'
     + reg_rows + '</table>' if regs else '<p><em>Keine Einträge</em></p>'}
    <h3>Essensspenden ({len(food)})</h3>
    {'<table border="1" cellpadding="4"><tr><th>Kategorie</th><th>Beschreibung</th><th>Kühlung</th></tr>'
     + food_rows + '</table>' if food else '<p><em>Keine Einträge</em></p>'}
    {_footer(base_url)}
    """


def build_welcome_email(name: str, instance_title: str, setup_url: str, base_url: str,
                        primary_color: str = '#4f46e5', logo_url: str = None) -> str:
    logo_html = (
        f'<div style="margin-bottom:16px">'
        f'<img src="{logo_url}" alt="{instance_title}" style="max-height:48px;max-width:200px;object-fit:contain">'
        f'</div>'
    ) if logo_url else ''
    return f"""
    {logo_html}
    <p>Hallo {name},</p>
    <p>du hast dich bei <strong>{instance_title}</strong> als Helfer registriert.</p>
    <p>Bitte klicke auf den folgenden Link, um dein Passwort einzurichten und dein Konto zu aktivieren.
    Dadurch kannst du deine Standdienste oder Essensspenden einsehen und bearbeiten.</p>
    <p><a href="{setup_url}" style="background:{primary_color};color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;">Passwort einrichten</a></p>
    <p>Der Link ist <strong>7 Tage</strong> gültig.</p>
    <p>Falls du keine Registrierung angefordert hast, kannst du diese E-Mail ignorieren.</p>
    {_footer(base_url)}
    """
