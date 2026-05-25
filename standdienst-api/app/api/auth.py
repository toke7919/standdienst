import hashlib
import logging
from datetime import datetime, timezone

import pyotp
from flask import Blueprint, request, session, current_app, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
    set_access_cookies, set_refresh_cookies, unset_jwt_cookies,
    verify_jwt_in_request,
)
from marshmallow import ValidationError

from ..extensions import db, limiter, _real_ip
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
    ip = _real_ip()

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
    ip = _real_ip()

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

    code = (request.get_json() or {}).get('code', '').strip().upper()
    role, user_id = pending['type'], pending['id']
    user = (Admin if role == 'admin' else Organizer).query.get(user_id)

    if not user or not user.totp_secret:
        return jsonify(error='Benutzer nicht gefunden'), 404

    totp = pyotp.TOTP(user.totp_secret)
    backup_used = False
    if totp.verify(code, valid_window=1):
        pass  # TOTP ok
    else:
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        stored = list(user.totp_backup_codes or [])
        if code_hash not in stored:
            return jsonify(error='Ungültiger Code'), 401
        stored.remove(code_hash)
        user.totp_backup_codes = stored
        backup_used = True

    access, refresh = _issue_tokens(user)
    _log_activity(ActivityLog.LOGIN_SUCCESS, _real_ip(),
                  user_name=user.email, actor_type=role)
    if backup_used:
        db.session.commit()
    resp = jsonify(user=_user_payload(user), backup_code_used=backup_used,
                   remaining_backup_codes=len(user.totp_backup_codes or []))
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

    import secrets as _secrets
    raw_codes = [_secrets.token_hex(4).upper() for _ in range(8)]
    code_hashes = [hashlib.sha256(c.encode()).hexdigest() for c in raw_codes]
    user.totp_secret = secret
    user.totp_enabled = True
    user.totp_backup_codes = code_hashes
    db.session.commit()
    return jsonify(message='2FA aktiviert', backup_codes=raw_codes), 200


@auth_bp.route('/2fa/disable', methods=['POST'])
@limiter.limit('5 per minute')
@jwt_required()
def disable_2fa():
    user = _load_user_by_identity(get_jwt_identity(), get_jwt().get('role'))
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404

    user.totp_secret = None
    user.totp_enabled = False
    user.totp_backup_codes = None
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
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            role = get_jwt().get('role')
            user = _load_user_by_identity(identity, role)
            if user and hasattr(user, 'rotate_jwt'):
                user.rotate_jwt()
                db.session.commit()
    except Exception:
        pass
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
    if hasattr(user, 'first_name'):
        payload['first_name'] = user.first_name
        payload['last_name'] = getattr(user, 'last_name', None)
    if hasattr(user, 'is_primary'):
        payload['is_primary'] = user.is_primary
    if hasattr(user, 'totp_enabled'):
        payload['totp_enabled'] = user.totp_enabled
    if hasattr(user, 'instance_id'):
        payload['instance_id'] = user.instance_id
    if hasattr(user, 'is_instance_admin'):
        payload['is_instance_admin'] = user.is_instance_admin
    if hasattr(user, 'instances') and user.role == 'organizer':
        from ..models.instance import organizer_instances as oi_table
        from ..extensions import db as _db
        insts = user.instances.all()
        admin_rows = {
            row.instance_id
            for row in _db.session.execute(
                oi_table.select().where(
                    oi_table.c.organizer_id == user.id,
                    oi_table.c.is_instance_admin == True,
                )
            ).fetchall()
        }
        payload['instances'] = [
            {'id': i.id, 'slug': i.slug, 'name': i.name, 'is_admin': i.id in admin_rows}
            for i in insts
        ]
    if hasattr(user, 'notifications_enabled'):
        payload['notifications_enabled'] = user.notifications_enabled
    if hasattr(user, 'email_confirmation_enabled'):
        payload['email_confirmation_enabled'] = user.email_confirmation_enabled
    if hasattr(user, 'role') and user.role in ('admin', 'organizer'):
        from ..models import PasskeyCredential
        if user.role == 'admin':
            has_pk = PasskeyCredential.query.filter_by(admin_id=user.id).first() is not None
        else:
            has_pk = PasskeyCredential.query.filter_by(organizer_id=user.id).first() is not None
        payload['has_passkey'] = has_pk
    return payload


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    claims = get_jwt()
    identity = get_jwt_identity()
    role = claims.get('role')
    user = _load_user_by_identity(identity, role)
    if not user or role not in ('admin', 'organizer'):
        return jsonify(error='Nicht erlaubt'), 403

    data = request.get_json() or {}

    if 'first_name' in data:
        user.first_name = (data['first_name'] or '').strip()
    if 'last_name' in data:
        user.last_name = (data['last_name'] or '').strip()
    if 'first_name' in data or 'last_name' in data:
        user.name = f'{user.first_name or ""} {user.last_name or ""}'.strip() or user.name
    if 'email' in data:
        email = (data['email'] or '').strip().lower()
        if email and email != user.email:
            duplicate = (Admin if role == 'admin' else Organizer).query.filter_by(email=email).first()
            if duplicate:
                return jsonify(error='E-Mail bereits vergeben'), 409
            user.email = email
    if data.get('password'):
        err = validate_password_strength(data['password'], role='admin')
        if err:
            return jsonify(error=err), 400
        user.set_password(data['password'])
        user.rotate_jwt()
    if 'notifications_enabled' in data and role == 'organizer':
        user.notifications_enabled = bool(data['notifications_enabled'])

    db.session.commit()
    from ..utils.responses import ok
    return ok(_user_payload(user))
