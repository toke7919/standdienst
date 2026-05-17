from flask import current_app
from flask_mail import Message
from ..extensions import mail


def send_mail(to: str, subject: str, html: str, sender_name: str = None):
    default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', '')
    sender = f'{sender_name} <{default_sender}>' if sender_name else default_sender
    msg = Message(subject=subject, recipients=[to], html=html, sender=sender)
    mail.send(msg)


def build_reset_email(name: str, reset_url: str, base_url: str) -> str:
    return f"""
    <p>Hallo {name},</p>
    <p>du hast eine Passwort-Zurücksetzung angefordert.</p>
    <p><a href="{reset_url}">Passwort zurücksetzen</a></p>
    <p>Der Link ist 1 Stunde gültig.</p>
    <p>Falls du keine Zurücksetzung angefordert hast, kannst du diese E-Mail ignorieren.</p>
    """


def build_registration_email(name: str, instance_title: str, login_url: str) -> str:
    return f"""
    <p>Hallo {name},</p>
    <p>deine Registrierung bei <strong>{instance_title}</strong> war erfolgreich.</p>
    <p><a href="{login_url}">Zum Login</a></p>
    """
