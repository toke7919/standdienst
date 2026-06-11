import re
from functools import wraps
from flask import jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from sqlalchemy import select

from ..extensions import db
from ..models import Admin, Organizer, Volunteer, Instance


def _load_user(identity: str):
    if identity.startswith('admin_'):
        return db.session.get(Admin, int(identity[6:]))
    if identity.startswith('organizer_'):
        return db.session.get(Organizer, int(identity[10:]))
    if identity.startswith('volunteer_'):
        return db.session.get(Volunteer, int(identity[10:]))
    return None


def _jwt_version_valid(user, claims: dict) -> bool:
    """Prüft ob das Token noch zur aktuellen DB-Version gehört."""
    token_version = claims.get('jwt_version', 1)
    return (user.jwt_version or 1) == token_version


def _resolve_instance(slug: str):
    instance = db.session.scalars(select(Instance).filter_by(slug=slug)).first()
    if not instance:
        return None, (jsonify(error='Instanz nicht gefunden'), 404)
    return instance, None


def require_admin(fn):
    """Nur Admins (kein Instanz-Kontext erforderlich)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify(error='Zugriff nur für Admins'), 403
        user = _load_user(get_jwt_identity())
        if not user or not _jwt_version_valid(user, claims):
            return jsonify(error='Sitzung abgelaufen – bitte erneut anmelden'), 401
        g.current_user = user
        g.role = 'admin'
        return fn(*args, **kwargs)
    return wrapper


def require_staff(fn):
    """Admin oder Organizer; bei URL-Parameter <slug> wird Instanz-Zugriff geprüft."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        role = claims.get('role')
        if role not in ('admin', 'organizer'):
            return jsonify(error='Zugriff verweigert'), 403

        user = _load_user(get_jwt_identity())
        if not user or not _jwt_version_valid(user, claims):
            return jsonify(error='Sitzung abgelaufen – bitte erneut anmelden'), 401
        g.current_user = user
        g.role = role

        slug = kwargs.get('slug')
        if slug:
            instance, err = _resolve_instance(slug)
            if err:
                return err
            if role == 'organizer' and not user.has_instance_access(instance.id):
                return jsonify(error='Kein Zugriff auf diese Instanz'), 403
            g.instance = instance

        return fn(*args, **kwargs)
    return wrapper


def require_instance_admin(fn):
    """Admin oder Organizer mit is_instance_admin=True; <slug> erforderlich."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        role = claims.get('role')
        if role not in ('admin', 'organizer'):
            return jsonify(error='Zugriff verweigert'), 403

        user = _load_user(get_jwt_identity())
        if not user or not _jwt_version_valid(user, claims):
            return jsonify(error='Sitzung abgelaufen – bitte erneut anmelden'), 401
        g.current_user = user
        g.role = role

        slug = kwargs.get('slug')
        if slug:
            instance, err = _resolve_instance(slug)
            if err:
                return err
            if role == 'organizer':
                if not user.has_instance_access(instance.id):
                    return jsonify(error='Kein Zugriff auf diese Instanz'), 403
                if not user.is_admin_for(instance.id):
                    return jsonify(error='Instanz-Admin-Berechtigung erforderlich'), 403
            g.instance = instance

        return fn(*args, **kwargs)
    return wrapper


def require_volunteer(fn):
    """Volunteer der richtigen Instanz (kein Soft-Delete)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') != 'volunteer':
            return jsonify(error='Zugriff verweigert'), 403

        volunteer = _load_user(get_jwt_identity())
        if not volunteer or volunteer.is_deleted:
            return jsonify(error='Konto nicht verfügbar'), 403
        if not _jwt_version_valid(volunteer, claims):
            return jsonify(error='Sitzung abgelaufen – bitte erneut anmelden'), 401

        slug = kwargs.get('slug')
        if slug:
            instance, err = _resolve_instance(slug)
            if err:
                return err
            if volunteer.instance_id != instance.id:
                return jsonify(error='Zugriff verweigert'), 403
            g.instance = instance

        g.current_user = volunteer
        g.role = 'volunteer'
        return fn(*args, **kwargs)
    return wrapper


def validate_password_strength(password: str, role: str = 'volunteer') -> bool:
    """Rollenabhängige Passwort-Validierung.

    Volunteers:        mind. 8 Zeichen
    Admins/Organizer:  mind. 12 Zeichen + Groß/Klein + Ziffer + Sonderzeichen
    """
    # bcrypt verarbeitet nur die ersten 72 Bytes; längere Passwörter würden
    # stillschweigend abgeschnitten (zwei verschiedene Passwörter mit gleichem
    # 72-Byte-Präfix kollidieren). Daher hart ablehnen.
    if len(password.encode('utf-8')) > 72:
        return False
    if role in ('admin', 'organizer'):
        if len(password) < 12:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        if not re.search(r'[^a-zA-Z0-9]', password):
            return False
    else:
        if len(password) < 8:
            return False
    return True
