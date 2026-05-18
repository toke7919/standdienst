from flask import current_app
from flask_mail import Message
from ..extensions import mail


def is_mail_configured(app=None) -> bool:
    """True wenn SMTP-Server konfiguriert ist."""
    cfg = (app or current_app).config
    return bool(cfg.get('MAIL_SERVER'))


def send_mail(to: str, subject: str, html: str, sender_name: str = None):
    default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', '')
    sender = f'{sender_name} <{default_sender}>' if sender_name else default_sender
    msg = Message(subject=subject, recipients=[to], html=html, sender=sender)
    mail.send(msg)


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


def build_welcome_email(name: str, instance_title: str, setup_url: str, base_url: str) -> str:
    return f"""
    <p>Hallo {name},</p>
    <p>du wurdest bei <strong>{instance_title}</strong> als Helfer registriert.</p>
    <p>Bitte klicke auf den folgenden Link, um dein Passwort einzurichten und dein Konto zu aktivieren:</p>
    <p><a href="{setup_url}" style="background:#4f46e5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;">Passwort einrichten</a></p>
    <p>Der Link ist <strong>7 Tage</strong> gültig.</p>
    <p>Falls du keine Registrierung angefordert hast, kannst du diese E-Mail ignorieren.</p>
    {_footer(base_url)}
    """
