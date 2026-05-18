"""Ersteinrichtungs-Blueprint – nur erreichbar solange setup_complete=False."""
import os
from flask import Blueprint, request, jsonify

from ..extensions import db
from ..models import Admin, GlobalSettings, MailSettings

setup_bp = Blueprint('setup', __name__)

_LOOPBACK = {'127.0.0.1', '::1', 'localhost'}


def _check_setup_ip():
    """Prüft ob die Request-IP auf der Setup-Allowlist steht.

    Ohne SETUP_ALLOWED_IPS darf nur localhost zugreifen. Mit gesetzter Env-Var
    werden die darin enthaltenen IPs (kommagetrennt) zusätzlich zugelassen.
    """
    allowed_env = os.environ.get('SETUP_ALLOWED_IPS', '')
    allowed = _LOOPBACK | {ip.strip() for ip in allowed_env.split(',') if ip.strip()}
    ip = request.remote_addr or ''
    if ip not in allowed:
        return jsonify(error='Setup-Zugriff von dieser IP nicht erlaubt'), 403
    return None


def _check_guard():
    """403 zurückgeben wenn Setup bereits abgeschlossen."""
    gs = GlobalSettings.query.first()
    if gs and gs.setup_complete:
        return jsonify(error='Setup bereits abgeschlossen'), 403
    return None


def _get_or_create_gs() -> GlobalSettings:
    gs = GlobalSettings.query.first()
    if not gs:
        gs = GlobalSettings()
        db.session.add(gs)
    return gs


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@setup_bp.route('/status', methods=['GET'])
def status():
    gs = GlobalSettings.query.first()
    return jsonify(data={
        'setup_complete': bool(gs and gs.setup_complete),
        'has_admin': Admin.query.count() > 0,
    })


# ---------------------------------------------------------------------------
# Schritt 1 – Admin-Account anlegen
# ---------------------------------------------------------------------------

@setup_bp.route('/admin', methods=['POST'])
def create_admin():
    err = _check_setup_ip() or _check_guard()
    if err:
        return err

    if Admin.query.count() > 0:
        return jsonify(error='Admin-Account existiert bereits'), 409

    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify(error='E-Mail und Passwort sind erforderlich'), 400

    from ..utils.auth import validate_password_strength
    if not validate_password_strength(password, role='admin'):
        return jsonify(error=(
            'Passwort zu schwach (mind. 12 Zeichen, '
            'Groß-/Kleinbuchstabe, Ziffer, Sonderzeichen)'
        )), 400

    admin = Admin(email=email, is_primary=True)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    return jsonify(message='Admin-Account angelegt'), 201


# ---------------------------------------------------------------------------
# Schritt 2 – Basis-Konfiguration (URL + GitHub PAT)
# ---------------------------------------------------------------------------

@setup_bp.route('/config', methods=['POST'])
def save_config():
    err = _check_setup_ip() or _check_guard()
    if err:
        return err

    data = request.get_json() or {}
    gs = _get_or_create_gs()
    base_url = (data.get('base_url') or '').rstrip('/')
    gs.base_url = base_url or None
    gs.github_pat = data.get('github_pat') or None
    gs.copyright_text = data.get('copyright_text') or None
    if data.get('timezone'):
        gs.timezone = data['timezone']
    db.session.commit()
    return jsonify(message='Konfiguration gespeichert')


# ---------------------------------------------------------------------------
# Schritt 3 – Mail-Server (optional)
# ---------------------------------------------------------------------------

@setup_bp.route('/mail', methods=['POST'])
def save_mail():
    err = _check_setup_ip() or _check_guard()
    if err:
        return err

    data = request.get_json() or {}
    ms = MailSettings.query.first()
    if not ms:
        ms = MailSettings()
        db.session.add(ms)

    ms.mail_server = data.get('server', '')
    ms.mail_port = int(data.get('port', 587))
    ms.mail_use_tls = bool(data.get('use_tls', True))
    ms.mail_username = data.get('username', '')
    ms.mail_password = data.get('password', '')
    ms.mail_default_sender = data.get('sender', '')
    ms.mail_sender_name = data.get('sender_name', '')
    db.session.commit()
    return jsonify(message='Mail-Einstellungen gespeichert')


# ---------------------------------------------------------------------------
# Abschluss – Setup als abgeschlossen markieren
# ---------------------------------------------------------------------------

@setup_bp.route('/finish', methods=['POST'])
def finish():
    err = _check_setup_ip() or _check_guard()
    if err:
        return err

    if Admin.query.count() == 0:
        return jsonify(error='Bitte zuerst einen Admin-Account anlegen (Schritt 1)'), 400

    gs = _get_or_create_gs()
    gs.setup_complete = True
    db.session.commit()
    return jsonify(message='Setup abgeschlossen – Standdienst ist bereit')
