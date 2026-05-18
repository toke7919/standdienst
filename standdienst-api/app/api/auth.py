import hashlib
import logging
from datetime import datetime, timezone

import pyotp
from flask import Blueprint, request, session, current_app, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
    set_access_cookies, set_refresh_cookies, unset_jwt_cookies,
)
from marshmallow import ValidationError

from ..extensions import db, limiter
from ..models import Admin, Organizer, Instance, ActivityLog
from ..utils.auth import validate_password_strength
from ..utils.mail import send_mail, build_reset_email

auth_bp = Blueprint('auth', __name__)
log = logging.getLogger(__name__)


def _log_activity(event_type, ip, user_name=None, actor_type='admin', details=None,
                  volunteer_id=None, instance_id=None):
    entry = ActivityLog(
        instance_id=instance_id,
        event_type=event_type,
        ip_address=ip,
        volunteer_name=user_name,
        volunteer_id=volunteer_id,
        actor_type=actor_type,
        details=details,
        user_agent=request.headers.get('User-Agent', '')[:500],
    )
    db.session.add(entry)
    db.session.commit()


def _fail2ban_log(ip, user):
    from ..utils.ip_whitelist import is_whitelisted
    if is_whitelisted(ip):
        return
    try:
        log_path = current_app.config.get('FAIL2BAN_LOG', 'logs/auth.log')
        with open(log_path, 'a') as f:
            f.write(f'{datetime.now(timezone.utc).isoformat()} LOGIN_FAIL ip={ip} user={user}\n')
    except OSError:
        pass


def _issue_tokens(user):
    identity = user.get_jwt_identity()
    claims = {
        'role': user.role,
        'name': getattr(user, 'name', user.email),
        'email': user.email,
        'jwt_version': user.jwt_version or 1,
    }
    access = create_access_token(identity=identity, additional_claims=claims)
    refresh = create_refresh_token(identity=identity, additional_claims=claims)
    return access, refresh


def _set_token_cookies(response, access, refresh):
    set_access_cookies(response, access)
    set_refresh_cookies(response, refresh)
    return response


# ---------------------------------------------------------------------------
# Login – Admin + Organizer
# ---------------------------------------------------------------------------

@auth_bp.route('/login', methods=['POST'])
@limiter.limit('5 per minute')
def login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')
    ip = request.remote_addr

    user = (Admin.query.filter_by(email=email).first()
            or Organizer.query.filter_by(email=email).first())

    if not user or not user.check_password(password):
        _fail2ban_log(ip, email)
        _log_activity(ActivityLog.LOGIN_FAIL, ip, user_name=email)
        return jsonify(error='Ungültige Anmeldedaten'), 401

    if user.totp_enabled:
        session['pending_2fa'] = {'type': user.role, 'id': user.id}
        return jsonify(requires_2fa=True, role=user.role), 200

    access, refresh = _issue_tokens(user)
    _log_activity(ActivityLog.LOGIN_SUCCESS, ip, user_name=email, actor_type=user.role)
    resp = jsonify(user=_user_payload(user))
    return _set_token_cookies(resp, access, refresh)


# ---------------------------------------------------------------------------
# Login – Volunteer
# ---------------------------------------------------------------------------

@auth_bp.route('/volunteer-login', methods=['POST'])
@limiter.limit('5 per minute')
def volunteer_login():
    from ..models import Volunteer
    data = request.get_json() or {}
    slug = (data.get('slug') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')
    ip = request.remote_addr

    instance = Instance.query.filter_by(slug=slug, is_active=True).first()
    if not instance:
        return jsonify(error='Instanz nicht gefunden'), 404

    volunteer = Volunteer.query.filter_by(instance_id=instance.id, email=email).first()

    if not volunteer or not volunteer.check_password(password) or volunteer.is_deleted:
        _fail2ban_log(ip, email)
        _log_activity(ActivityLog.LOGIN_FAIL, ip, user_name=email, actor_type='volunteer',
                      instance_id=instance.id)
        return jsonify(error='Ungültige Anmeldedaten'), 401

    access, refresh = _issue_tokens(volunteer)
    _log_activity(ActivityLog.LOGIN_SUCCESS, ip, user_name=email,
                  volunteer_id=volunteer.id, actor_type='volunteer', instance_id=instance.id)
    resp = jsonify(user=_user_payload(volunteer))
    return _set_token_cookies(resp, access, refresh)


# ---------------------------------------------------------------------------
# 2FA
# ---------------------------------------------------------------------------

@auth_bp.route('/2fa/verify', methods=['POST'])
@limiter.limit('10 per minute')
def verify_2fa():
    pending = session.pop('pending_2fa', None)
    if not pending:
        return jsonify(error='Keine ausstehende 2FA-Verifizierung'), 400

    code = (request.get_json() or {}).get('code', '').strip()
    role, user_id = pending['type'], pending['id']
    user = (Admin if role == 'admin' else Organizer).query.get(user_id)

    if not user or not user.totp_secret:
        return jsonify(error='Benutzer nicht gefunden'), 404

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code, valid_window=1):
        return jsonify(error='Ungültiger Code'), 401

    access, refresh = _issue_tokens(user)
    _log_activity(ActivityLog.LOGIN_SUCCESS, request.remote_addr,
                  user_name=user.email, actor_type=role)
    resp = jsonify(user=_user_payload(user))
    return _set_token_cookies(resp, access, refresh)


@auth_bp.route('/2fa/setup', methods=['POST'])
@limiter.limit('10 per minute')
@jwt_required()
def setup_2fa():
    identity = get_jwt_identity()
    role = get_jwt().get('role')
    user = _load_user_by_identity(identity, role)
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404

    secret = pyotp.random_base32()
    session['totp_setup_secret'] = secret
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(user.email, issuer_name='Standdienst')
    return jsonify(secret=secret, otpauth_url=uri), 200


@auth_bp.route('/2fa/confirm', methods=['POST'])
@limiter.limit('10 per minute')
@jwt_required()
def confirm_2fa():
    identity = get_jwt_identity()
    role = get_jwt().get('role')
    user = _load_user_by_identity(identity, role)
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404

    secret = session.pop('totp_setup_secret', None)
    code = (request.get_json() or {}).get('code', '').strip()
    if not secret or not pyotp.TOTP(secret).verify(code, valid_window=1):
        return jsonify(error='Ungültiger Code'), 401

    user.totp_secret = secret
    user.totp_enabled = True
    db.session.commit()
    return jsonify(message='2FA aktiviert'), 200


@auth_bp.route('/2fa/disable', methods=['POST'])
@limiter.limit('5 per minute')
@jwt_required()
def disable_2fa():
    user = _load_user_by_identity(get_jwt_identity(), get_jwt().get('role'))
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404

    user.totp_secret = None
    user.totp_enabled = False
    db.session.commit()
    return jsonify(message='2FA deaktiviert'), 200


# ---------------------------------------------------------------------------
# Token-Refresh + Logout
# ---------------------------------------------------------------------------

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get('role')
    user = _load_user_by_identity(identity, role)
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404

    token_version = claims.get('jwt_version', 1)
    if (user.jwt_version or 1) != token_version:
        resp = jsonify(error='Sitzung abgelaufen – bitte erneut anmelden')
        unset_jwt_cookies(resp)
        return resp, 401

    access = create_access_token(
        identity=identity,
        additional_claims={
            'role': role,
            'email': claims.get('email'),
            'name': claims.get('name'),
            'jwt_version': user.jwt_version or 1,
        },
    )
    resp = jsonify(message='Token erneuert')
    set_access_cookies(resp, access)
    return resp


@auth_bp.route('/logout', methods=['POST'])
def logout():
    resp = jsonify(message='Abgemeldet')
    unset_jwt_cookies(resp)
    session.clear()
    return resp


# ---------------------------------------------------------------------------
# Passwort-Reset – Admin/Organizer
# ---------------------------------------------------------------------------

@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit('5 per minute')
def forgot_password():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    user_type = data.get('type', 'admin')

    user = (Admin if user_type == 'admin' else Organizer).query.filter_by(email=email).first()
    if user:
        raw_token = user.generate_reset_token()
        db.session.commit()
        base_url = current_app.config.get('FRONTEND_URL', '')
        reset_url = f'{base_url}/admin/reset-password?token={raw_token}'
        try:
            send_mail(email, 'Passwort zurücksetzen',
                      build_reset_email(getattr(user, 'name', email), reset_url, base_url))
        except Exception:
            pass

    return jsonify(message='Falls die E-Mail-Adresse bekannt ist, wurde eine E-Mail gesendet'), 200


@auth_bp.route('/reset-password', methods=['POST'])
@limiter.limit('10 per minute')
def reset_password():
    data = request.get_json() or {}
    raw_token = data.get('token', '')
    new_password = data.get('password', '')
    user_type = data.get('type', 'admin')
    role = 'admin' if user_type == 'admin' else 'organizer'

    if not validate_password_strength(new_password, role=role):
        return jsonify(error=(
            'Passwort zu schwach (mind. 12 Zeichen, '
            'Groß-/Kleinbuchstabe, Ziffer, Sonderzeichen)'
        )), 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    model = Admin if user_type == 'admin' else Organizer
    user = model.query.filter_by(reset_token=token_hash).first()

    if not user or not user.is_reset_token_valid:
        return jsonify(error='Ungültiger oder abgelaufener Reset-Link'), 400

    user.set_password(new_password)
    user.rotate_jwt()
    user.clear_reset_token()
    db.session.commit()
    return jsonify(message='Passwort wurde geändert'), 200


# ---------------------------------------------------------------------------
# Me – aktueller Nutzer
# ---------------------------------------------------------------------------

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    claims = get_jwt()
    identity = get_jwt_identity()
    user = _load_user_by_identity(identity, claims.get('role'))
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404
    return jsonify(user=_user_payload(user)), 200


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _load_user_by_identity(identity: str, role: str):
    from ..models import Volunteer
    try:
        uid = int(identity.split('_')[1])
    except (IndexError, ValueError):
        return None
    if role == 'admin':
        return db.session.get(Admin, uid)
    if role == 'organizer':
        return db.session.get(Organizer, uid)
    if role == 'volunteer':
        return db.session.get(Volunteer, uid)
    return None


def _user_payload(user) -> dict:
    payload = {'id': user.id, 'email': user.email, 'role': user.role}
    if hasattr(user, 'name'):
        payload['name'] = user.name
    if hasattr(user, 'is_primary'):
        payload['is_primary'] = user.is_primary
    if hasattr(user, 'totp_enabled'):
        payload['totp_enabled'] = user.totp_enabled
    if hasattr(user, 'instance_id'):
        payload['instance_id'] = user.instance_id
    return payload
