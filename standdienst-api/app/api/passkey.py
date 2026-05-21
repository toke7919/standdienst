import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import webauthn
from flask import Blueprint, current_app, jsonify, request, session
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from ..extensions import db, limiter
from ..models import Admin, Organizer, ActivityLog
from ..models.passkey import PasskeyCredential

passkey_bp = Blueprint('passkey', __name__)
log = logging.getLogger(__name__)

MAX_PASSKEYS = 5


def _rp_config():
    # Expliziter Override hat höchste Priorität (z.B. WEBAUTHN_ORIGIN=https://example.com)
    explicit_origin = current_app.config.get('WEBAUTHN_ORIGIN', '')
    if explicit_origin:
        parsed_exp = urlparse(explicit_origin)
        rp_id = current_app.config.get('WEBAUTHN_RP_ID') or (parsed_exp.hostname or '')
        return rp_id, explicit_origin.rstrip('/')

    frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
    parsed = urlparse(frontend_url)
    try:
        from flask import request as _req
        fwd_host = _req.headers.get('X-Forwarded-Host', '').split(',')[0].strip()
        host = fwd_host or parsed.netloc
        # X-Forwarded-Proto wird von nginx auf das Client-seitige Protokoll gesetzt
        # (proxy_set_header X-Forwarded-Proto $scheme) – authoritative für WebAuthn-Origin
        fwd_proto = _req.headers.get('X-Forwarded-Proto', '').split(',')[0].strip()
        proto = fwd_proto or parsed.scheme
    except RuntimeError:
        host = parsed.netloc
        proto = parsed.scheme
    # Standard-Ports entfernen, damit origin exakt übereinstimmt
    if (proto == 'https' and host.endswith(':443')) or (proto == 'http' and host.endswith(':80')):
        host = host.rsplit(':', 1)[0]
    rp_id = current_app.config.get('WEBAUTHN_RP_ID') or host.split(':')[0]
    origin = f'{proto}://{host}'
    return rp_id, origin


def _user_credentials(role, user_id):
    if role == 'admin':
        return PasskeyCredential.query.filter_by(admin_id=user_id).all()
    return PasskeyCredential.query.filter_by(organizer_id=user_id).all()


def _load_user(identity, role):
    try:
        uid = int(identity.split('_')[1])
    except (IndexError, ValueError):
        return None
    if role == 'admin':
        return db.session.get(Admin, uid)
    if role == 'organizer':
        return db.session.get(Organizer, uid)
    return None


def _serialize(pk: PasskeyCredential) -> dict:
    return {
        'id': pk.id,
        'name': pk.name,
        'created_at': pk.created_at.isoformat() if pk.created_at else None,
        'last_used_at': pk.last_used_at.isoformat() if pk.last_used_at else None,
    }


# ---------------------------------------------------------------------------
# Registrierung (setzt eingeloggten Admin/Org voraus)
# ---------------------------------------------------------------------------

@passkey_bp.route('/register/begin', methods=['POST'])
@limiter.limit('10 per minute')
@jwt_required()
def register_begin():
    identity = get_jwt_identity()
    role = get_jwt().get('role')
    if role not in ('admin', 'organizer'):
        return jsonify(error='Nur für Admins und Organisatoren'), 403

    user = _load_user(identity, role)
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404

    existing = _user_credentials(role, user.id)
    if len(existing) >= MAX_PASSKEYS:
        return jsonify(error=f'Maximal {MAX_PASSKEYS} Passkeys erlaubt'), 400

    exclude = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(pk.credential_id))
        for pk in existing
    ]

    rp_id, _ = _rp_config()
    options = webauthn.generate_registration_options(
        rp_id=rp_id,
        rp_name='Standdienst',
        user_id=identity.encode(),
        user_name=user.email,
        user_display_name=getattr(user, 'name', user.email),
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )

    session['passkey_reg_challenge'] = bytes_to_base64url(options.challenge)
    session['passkey_reg_identity'] = identity
    return jsonify(json.loads(webauthn.options_to_json(options))), 200


@passkey_bp.route('/register/complete', methods=['POST'])
@limiter.limit('10 per minute')
@jwt_required()
def register_complete():
    identity = get_jwt_identity()
    role = get_jwt().get('role')
    if role not in ('admin', 'organizer'):
        return jsonify(error='Nur für Admins und Organisatoren'), 403

    user = _load_user(identity, role)
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404

    challenge_b64 = session.pop('passkey_reg_challenge', None)
    reg_identity = session.pop('passkey_reg_identity', None)
    if not challenge_b64 or reg_identity != identity:
        return jsonify(error='Keine ausstehende Registrierung'), 400

    data = request.get_json() or {}
    passkey_name = str(data.get('name') or 'Passkey')[:100]

    try:
        rp_id, origin = _rp_config()
        verification = webauthn.verify_registration_response(
            credential=data,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=rp_id,
            expected_origin=origin,
        )
    except Exception as e:
        log.warning('Passkey-Registrierung fehlgeschlagen (rp_id=%s, origin=%s): %s', rp_id, origin, e)
        return jsonify(error=f'Passkey-Verifizierung fehlgeschlagen. Erwartet: {origin}'), 400

    pk = PasskeyCredential(
        admin_id=user.id if role == 'admin' else None,
        organizer_id=user.id if role == 'organizer' else None,
        credential_id=bytes_to_base64url(verification.credential_id),
        public_key=bytes_to_base64url(verification.credential_public_key),
        sign_count=verification.sign_count,
        name=passkey_name,
    )
    db.session.add(pk)
    db.session.commit()

    return jsonify(message='Passkey registriert', credential=_serialize(pk)), 201


# ---------------------------------------------------------------------------
# Authentifizierung (kein Login erforderlich)
# ---------------------------------------------------------------------------

@passkey_bp.route('/authenticate/begin', methods=['POST'])
@limiter.limit('20 per minute')
def authenticate_begin():
    rp_id, _ = _rp_config()
    options = webauthn.generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=[],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    session['passkey_auth_challenge'] = bytes_to_base64url(options.challenge)
    return jsonify(json.loads(webauthn.options_to_json(options))), 200


@passkey_bp.route('/authenticate/complete', methods=['POST'])
@limiter.limit('20 per minute')
def authenticate_complete():
    challenge_b64 = session.pop('passkey_auth_challenge', None)
    if not challenge_b64:
        return jsonify(error='Keine ausstehende Authentifizierung'), 400

    data = request.get_json() or {}
    cred_id = data.get('id', '')
    pk = PasskeyCredential.query.filter_by(credential_id=cred_id).first()
    if not pk:
        return jsonify(error='Passkey nicht gefunden'), 401

    try:
        rp_id, origin = _rp_config()
        verification = webauthn.verify_authentication_response(
            credential=data,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=base64url_to_bytes(pk.public_key),
            credential_current_sign_count=pk.sign_count,
        )
    except Exception as e:
        log.warning('Passkey-Authentifizierung fehlgeschlagen: %s', e)
        return jsonify(error='Passkey-Verifizierung fehlgeschlagen'), 401

    pk.sign_count = verification.new_sign_count
    pk.last_used_at = datetime.now(timezone.utc)
    db.session.commit()

    identity = pk.owner_identity()
    role = identity.split('_')[0]
    uid = int(identity.split('_')[1])
    user = db.session.get(Admin if role == 'admin' else Organizer, uid)
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404

    from .auth import _issue_tokens, _set_token_cookies, _log_activity
    access, refresh = _issue_tokens(user)
    _log_activity(ActivityLog.LOGIN_SUCCESS, request.remote_addr,
                  user_name=user.email, actor_type=role)
    resp = jsonify(user={'id': user.id, 'email': user.email, 'role': role,
                         'name': getattr(user, 'name', user.email)})
    return _set_token_cookies(resp, access, refresh)


# ---------------------------------------------------------------------------
# Passkey-Verwaltung (setzt eingeloggten Admin/Org voraus)
# ---------------------------------------------------------------------------

@passkey_bp.route('/credentials', methods=['GET'])
@jwt_required()
def list_credentials():
    identity = get_jwt_identity()
    role = get_jwt().get('role')
    user = _load_user(identity, role)
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404

    credentials = _user_credentials(role, user.id)
    return jsonify(credentials=[_serialize(pk) for pk in credentials]), 200


@passkey_bp.route('/credentials/<int:pk_id>', methods=['DELETE'])
@jwt_required()
def delete_credential(pk_id):
    identity = get_jwt_identity()
    role = get_jwt().get('role')
    user = _load_user(identity, role)
    if not user:
        return jsonify(error='Benutzer nicht gefunden'), 404

    pk = db.session.get(PasskeyCredential, pk_id)
    if not pk:
        return jsonify(error='Passkey nicht gefunden'), 404

    if role == 'admin' and pk.admin_id != user.id:
        return jsonify(error='Zugriff verweigert'), 403
    if role == 'organizer' and pk.organizer_id != user.id:
        return jsonify(error='Zugriff verweigert'), 403

    db.session.delete(pk)
    db.session.commit()
    return jsonify(message='Passkey gelöscht'), 200
