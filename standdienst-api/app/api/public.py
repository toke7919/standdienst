import hashlib
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError

from ..extensions import db, limiter, _real_ip
from ..models import Instance, SiteSettings, ActivityLog, Volunteer
from ..schemas.volunteer import VolunteerRegisterSchema
from ..utils.settings_cache import get_global_settings
from ..utils.auth import validate_password_strength
from ..utils.captcha import generate_challenge, verify_solution
from ..utils.mail import (
    is_mail_configured, send_mail, get_effective_logo_for_email,
    build_reset_email, build_welcome_email, build_registration_email,
)

public_bp = Blueprint('public', __name__)

_register_schema = VolunteerRegisterSchema()


def _base_url() -> str:
    """Ermittelt die Basis-URL.

    Priorität: 1. GlobalSettings.base_url (Setup-Wizard)
               2. FRONTEND_URL Umgebungsvariable
               3. X-Forwarded-Host / Host-Header (Reverse-Proxy-Fallback)
    """
    try:
        gs = get_global_settings()
        if gs and gs.base_url:
            return gs.base_url.rstrip('/')
    except Exception:
        pass
    cfg = current_app.config.get('FRONTEND_URL', '').rstrip('/')
    if cfg and 'localhost' not in cfg and '127.0.0.1' not in cfg:
        return cfg
    host = request.headers.get('X-Forwarded-Host') or request.headers.get('Host', 'localhost')
    proto = request.headers.get('X-Forwarded-Proto', 'http').split(',')[0].strip()
    return f'{proto}://{host}'


@public_bp.route('/platform-info', methods=['GET'])
def platform_info():
    gs = get_global_settings()
    return jsonify(data={
        'copyright_text': gs.copyright_text if gs else '',
        'has_impressum': bool(gs and gs.provider_impressum_html) if gs else True,
    }), 200


@public_bp.route('/instances', methods=['GET'])
def list_instances():
    instances = Instance.query.filter_by(is_active=True).order_by(Instance.name).all()
    return jsonify(data=[{'slug': i.slug, 'name': i.name} for i in instances]), 200


@public_bp.route('/<slug>/info', methods=['GET'])
def instance_info(slug):
    instance = Instance.query.filter_by(slug=slug, is_active=True).first()
    if not instance:
        return jsonify(error='Instanz nicht gefunden'), 404
    settings = SiteSettings.query.filter_by(instance_id=instance.id).first()
    global_settings = get_global_settings()
    return jsonify(data=_build_instance_info(instance, settings, global_settings)), 200


@public_bp.route('/<slug>/captcha', methods=['GET'])
def captcha(slug):
    return jsonify(generate_challenge()), 200


# ---------------------------------------------------------------------------
# Registrierung – passwortloser Flow
# ---------------------------------------------------------------------------

@public_bp.route('/<slug>/register', methods=['POST'])
@limiter.limit('10 per minute')
def register(slug):
    instance = Instance.query.filter_by(slug=slug, is_active=True).first()
    if not instance:
        return jsonify(error='Instanz nicht gefunden'), 404

    settings = SiteSettings.query.filter_by(instance_id=instance.id).first()
    if settings and settings.site_locked:
        return jsonify(error='Anmeldung ist gesperrt'), 403
    if settings and not settings.registration_open:
        return jsonify(error='Anmeldeschluss ist überschritten'), 403

    try:
        data = _register_schema.load(request.get_json() or {})
    except ValidationError as e:
        return jsonify(error='Validierungsfehler', errors=e.messages), 422

    if not verify_solution(data['altcha']):
        return jsonify(error='CAPTCHA-Verifizierung fehlgeschlagen'), 400

    gs = get_global_settings()
    has_policy = bool(
        (settings and settings.privacy_policy_html)
        or (gs and gs.datenschutz_template_html)
    )
    if has_policy and not data.get('consent'):
        return jsonify(error='Datenschutzzustimmung erforderlich'), 400

    email = (data.get('email') or '').strip().lower() or None

    if email and not is_mail_configured():
        return jsonify(error='E-Mail-Registrierung nicht verfügbar – SMTP nicht konfiguriert'), 503

    if email and Volunteer.query.filter_by(instance_id=instance.id, email=email).first():
        return jsonify(error='E-Mail-Adresse bereits vergeben'), 409

    first_name = data['first_name'].strip()
    last_name = (data.get('last_name') or '').strip()
    full_name = f'{first_name} {last_name}'.strip()

    volunteer = Volunteer(
        instance_id=instance.id,
        name=full_name,
        first_name=first_name,
        last_name=last_name,
        email=email,
        consent_given_at=datetime.now(timezone.utc) if data.get('consent') else None,
    )
    db.session.add(volunteer)
    db.session.flush()

    db.session.add(ActivityLog(
        instance_id=instance.id,
        event_type=ActivityLog.VOLUNTEER_REGISTER,
        volunteer_name=full_name,
        ip_address=_real_ip(),
        actor_type='volunteer',
        user_agent=request.headers.get('User-Agent', '')[:500],
    ))

    if email:
        raw_token = volunteer.generate_welcome_token()
        db.session.commit()

        title = settings.site_title if settings else instance.name
        base_url = _base_url()
        setup_url = f'{base_url}/{slug}/welcome/{raw_token}'
        primary_color = settings.primary_color if settings else None
        logo_url = get_effective_logo_for_email(settings.logo_filename if settings else None, base_url)
        global_settings = get_global_settings()
        copyright_text = global_settings.copyright_text if global_settings else None
        try:
            kw = dict(logo_url=logo_url, slug=slug, copyright_text=copyright_text,
                      show_branding=settings.branding_enabled if settings else True)
            if primary_color:
                kw['primary_color'] = primary_color
            send_mail(email, f'Willkommen bei {title}',
                      build_welcome_email(volunteer.name, title, setup_url, base_url, **kw),
                      sender_name=title)
        except Exception:
            pass

        from ..api.auth import _issue_tokens, _set_token_cookies, _user_payload
        access, refresh = _issue_tokens(volunteer)
        resp = jsonify(user=_user_payload(volunteer), message='E-Mail mit Einrichtungslink gesendet')
        resp.status_code = 201
        return _set_token_cookies(resp, access, refresh)

    else:
        db.session.commit()
        from ..api.auth import _issue_tokens, _set_token_cookies, _user_payload
        access, refresh = _issue_tokens(volunteer)
        resp = jsonify(user=_user_payload(volunteer), message='Registrierung erfolgreich')
        resp.status_code = 201
        return _set_token_cookies(resp, access, refresh)


# ---------------------------------------------------------------------------
# Welcome-Token – Passwort einrichten
# ---------------------------------------------------------------------------

@public_bp.route('/<slug>/welcome/<raw_token>', methods=['GET'])
@limiter.limit('20 per hour')
def welcome_info(slug, raw_token):
    volunteer = _find_volunteer_by_welcome_token(slug, raw_token)
    if not volunteer:
        return jsonify(error='Ungültiger oder abgelaufener Einrichtungslink'), 400
    return jsonify(data={'name': volunteer.name, 'slug': slug}), 200


@public_bp.route('/<slug>/welcome/<raw_token>', methods=['POST'])
@limiter.limit('10 per minute')
def welcome_setup(slug, raw_token):
    volunteer = _find_volunteer_by_welcome_token(slug, raw_token)
    if not volunteer:
        return jsonify(error='Ungültiger oder abgelaufener Einrichtungslink'), 400

    password = (request.get_json() or {}).get('password', '')
    if not validate_password_strength(password, role='volunteer'):
        return jsonify(error='Passwort zu schwach (mind. 8 Zeichen)', ), 400

    volunteer.set_password(password)
    volunteer.clear_welcome_token()
    db.session.commit()

    from ..api.auth import _issue_tokens, _set_token_cookies, _user_payload
    access, refresh = _issue_tokens(volunteer)
    resp = jsonify(user=_user_payload(volunteer), message='Passwort eingerichtet')
    return _set_token_cookies(resp, access, refresh)


# ---------------------------------------------------------------------------
# Impressum + Datenschutz
# ---------------------------------------------------------------------------

@public_bp.route('/impressum', methods=['GET'])
def platform_impressum():
    gs = get_global_settings()
    html = _render_template(
        gs.impressum_template_html if gs else None,
        _contact_vars(gs),
    )
    return jsonify(data={
        'html': html,
        'context': 'platform',
    }), 200


@public_bp.route('/datenschutz', methods=['GET'])
def platform_datenschutz():
    gs = get_global_settings()
    html = _render_template(
        gs.datenschutz_template_html if gs else None,
        _contact_vars(gs),
    )
    return jsonify(data={
        'privacy_policy_html': html,
        'context': 'platform',
    }), 200


@public_bp.route('/<slug>/impressum', methods=['GET'])
def instance_impressum(slug):
    instance = Instance.query.filter_by(slug=slug, is_active=True).first()
    if not instance:
        return jsonify(error='Instanz nicht gefunden'), 404
    gs = get_global_settings()
    html = _render_template(
        gs.impressum_template_html if gs else None,
        _contact_vars(instance),
    )
    operator_html = gs.provider_impressum_html if gs else None
    return jsonify(data={
        'html': html,
        'operator_html': operator_html,
        'instance_name': instance.name,
        'slug': slug,
        'context': 'instance',
    }), 200


@public_bp.route('/<slug>/datenschutz', methods=['GET'])
def datenschutz(slug):
    instance = Instance.query.filter_by(slug=slug, is_active=True).first()
    if not instance:
        return jsonify(error='Instanz nicht gefunden'), 404
    gs = get_global_settings()
    html = _render_template(
        gs.datenschutz_template_html if gs else None,
        _contact_vars(instance),
    )
    settings = SiteSettings.query.filter_by(instance_id=instance.id).first()
    # Fallback auf altes Feld wenn kein Template gesetzt
    if not html and settings:
        html = settings.privacy_policy_html
    return jsonify(data={
        'privacy_policy_html': html,
        'instance_name': instance.name,
        'slug': slug,
    }), 200


# ---------------------------------------------------------------------------
# Passwort-Reset
# ---------------------------------------------------------------------------

@public_bp.route('/<slug>/forgot-password', methods=['POST'])
@limiter.limit('5 per minute')
def volunteer_forgot_password(slug):
    instance = Instance.query.filter_by(slug=slug, is_active=True).first()
    if not instance:
        return jsonify(error='Instanz nicht gefunden'), 404

    email = ((request.get_json() or {}).get('email') or '').strip().lower()
    volunteer = Volunteer.query.filter_by(instance_id=instance.id, email=email).first()

    if volunteer and not volunteer.is_deleted and is_mail_configured():
        raw_token = volunteer.generate_reset_token()
        db.session.commit()
        base_url = _base_url()
        reset_url = f'{base_url}/{slug}/reset-password?token={raw_token}'
        settings = SiteSettings.query.filter_by(instance_id=instance.id).first()
        title = settings.site_title if settings else instance.name
        primary_color = settings.primary_color if settings else None
        logo_url = get_effective_logo_for_email(settings.logo_filename if settings else None, base_url)
        global_settings = get_global_settings()
        copyright_text = global_settings.copyright_text if global_settings else None
        try:
            kw = dict(title=title, slug=slug, logo_url=logo_url, copyright_text=copyright_text,
                      show_branding=settings.branding_enabled if settings else True)
            if primary_color:
                kw['primary_color'] = primary_color
            send_mail(email, 'Passwort zurücksetzen',
                      build_reset_email(volunteer.name, reset_url, base_url, **kw),
                      sender_name=title)
        except Exception:
            pass

    return jsonify(message='Falls die E-Mail bekannt ist, wurde eine E-Mail gesendet'), 200


@public_bp.route('/<slug>/reset-password', methods=['POST'])
@limiter.limit('10 per minute')
def volunteer_reset_password(slug):
    instance = Instance.query.filter_by(slug=slug, is_active=True).first()
    if not instance:
        return jsonify(error='Instanz nicht gefunden'), 404

    data = request.get_json() or {}
    raw_token = data.get('token', '')
    new_password = data.get('password', '')

    if not validate_password_strength(new_password, role='volunteer'):
        return jsonify(error='Passwort zu schwach (mind. 8 Zeichen)'), 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    volunteer = Volunteer.query.filter_by(
        instance_id=instance.id, reset_token=token_hash
    ).first()

    if not volunteer or not volunteer.is_reset_token_valid or volunteer.is_deleted:
        return jsonify(error='Ungültiger oder abgelaufener Reset-Link'), 400

    volunteer.set_password(new_password)
    volunteer.rotate_jwt()
    volunteer.clear_reset_token()
    db.session.commit()
    return jsonify(message='Passwort wurde geändert'), 200


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _find_volunteer_by_welcome_token(slug: str, raw_token: str):
    instance = Instance.query.filter_by(slug=slug, is_active=True).first()
    if not instance:
        return None
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    volunteer = Volunteer.query.filter_by(
        instance_id=instance.id, welcome_token=token_hash
    ).first()
    if not volunteer or not volunteer.is_welcome_token_valid or volunteer.is_deleted:
        return None
    return volunteer


def _build_instance_info(instance, settings, global_settings) -> dict:
    has_policy = bool(
        (settings and settings.privacy_policy_html)
        or (global_settings and global_settings.datenschutz_template_html)
    )
    return {
        'id': instance.id,
        'slug': instance.slug,
        'name': instance.name,
        'title': settings.site_title if settings else instance.name,
        'primary_color': settings.primary_color if settings else None,
        'logo_filename': settings.logo_filename if settings else None,
        'site_locked': settings.site_locked if settings else False,
        'lock_message': settings.lock_message if settings else None,
        'site_title': settings.site_title if settings else instance.name,
        'shifts_enabled': settings.shifts_enabled if settings else True,
        'food_donations_enabled': settings.food_donations_enabled if settings else True,
        'registration_open': settings.registration_open if settings else True,
        'has_privacy_policy': has_policy,
        'mail_enabled': is_mail_configured(),
        'impressum_html': _merge_impressum(settings, global_settings),
        'copyright_text': global_settings.copyright_text if global_settings else '',
        'unregister_deadline_hours': settings.unregister_deadline_hours if settings else None,
        'branding_enabled': settings.branding_enabled if settings else True,
    }


def _merge_impressum(settings, global_settings) -> str:
    parts = []
    if global_settings and global_settings.provider_impressum_html:
        parts.append(global_settings.provider_impressum_html)
    if settings and settings.instance_impressum_html:
        parts.append(settings.instance_impressum_html)
    return '\n'.join(parts)


def _contact_vars(obj) -> dict:
    """Extrahiert Kontakt-Platzhalter aus GlobalSettings oder Instance."""
    if obj is None:
        return {}
    return {
        'person':       getattr(obj, 'contact_person', '') or '',
        'organisation': getattr(obj, 'contact_organisation', '') or getattr(obj, 'contact_person', '') or '',
        'adresse':      getattr(obj, 'contact_street', '') or '',
        'plz_ort':      getattr(obj, 'contact_zip_city', '') or '',
        'email':        getattr(obj, 'contact_email', '') or '',
        'telefon':      getattr(obj, 'contact_phone', '') or '',
        'asp':          getattr(obj, 'contact_asp', '') or getattr(obj, 'contact_person', '') or '',
        'asp-email':    getattr(obj, 'contact_asp_email', '') or getattr(obj, 'contact_email', '') or '',
    }


def _render_template(template_html: str | None, vars: dict) -> str | None:
    if not template_html:
        return None
    result = template_html
    for key, value in vars.items():
        result = result.replace('{{' + key + '}}', value)
    return result
