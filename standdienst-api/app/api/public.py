import hashlib
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError

from ..extensions import db, limiter
from ..models import Instance, SiteSettings, GlobalSettings, ActivityLog, Volunteer
from ..schemas.volunteer import VolunteerRegisterSchema
from ..utils.auth import validate_password_strength
from ..utils.captcha import generate_captcha, verify_captcha
from ..utils.mail import send_mail, build_reset_email, build_registration_email

public_bp = Blueprint('public', __name__)

_register_schema = VolunteerRegisterSchema()


@public_bp.route('/instances', methods=['GET'])
def list_instances():
    instances = Instance.query.filter_by(is_active=True).order_by(Instance.name).all()
    return jsonify(data=[
        {'slug': i.slug, 'name': i.name} for i in instances
    ]), 200


@public_bp.route('/<slug>/info', methods=['GET'])
def instance_info(slug):
    instance = Instance.query.filter_by(slug=slug, is_active=True).first()
    if not instance:
        return jsonify(error='Instanz nicht gefunden'), 404
    settings = SiteSettings.query.filter_by(instance_id=instance.id).first()
    global_settings = GlobalSettings.query.first()
    return jsonify(data=_build_instance_info(instance, settings, global_settings)), 200


@public_bp.route('/<slug>/captcha', methods=['GET'])
def captcha(slug):
    return jsonify(generate_captcha()), 200


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

    if not verify_captcha(data['captcha_answer']):
        return jsonify(error='Falsches CAPTCHA'), 400
    if not data.get('consent'):
        return jsonify(error='Datenschutzzustimmung erforderlich'), 400
    if not validate_password_strength(data['password']):
        return jsonify(error='Passwort zu schwach (mind. 8 Zeichen, 1 Ziffer, 1 Sonderzeichen)'), 400

    email = data['email'].strip().lower()
    if Volunteer.query.filter_by(instance_id=instance.id, email=email).first():
        return jsonify(error='E-Mail-Adresse bereits vergeben'), 409

    volunteer = Volunteer(
        instance_id=instance.id,
        name=data['name'].strip(),
        email=email,
        consent_given_at=datetime.now(timezone.utc),
    )
    volunteer.set_password(data['password'])
    db.session.add(volunteer)

    db.session.add(ActivityLog(
        instance_id=instance.id,
        event_type=ActivityLog.VOLUNTEER_REGISTER,
        volunteer_name=volunteer.name,
        ip_address=request.remote_addr,
        actor_type='volunteer',
    ))
    db.session.commit()

    try:
        title = settings.site_title if settings else instance.name
        base_url = current_app.config.get('FRONTEND_URL', '')
        send_mail(email, f'Registrierung bei {title}',
                  build_registration_email(volunteer.name, title, f'{base_url}/{slug}/login'))
    except Exception:
        pass

    return jsonify(message='Registrierung erfolgreich'), 201


@public_bp.route('/<slug>/forgot-password', methods=['POST'])
@limiter.limit('5 per minute')
def volunteer_forgot_password(slug):
    instance = Instance.query.filter_by(slug=slug, is_active=True).first()
    if not instance:
        return jsonify(error='Instanz nicht gefunden'), 404

    email = ((request.get_json() or {}).get('email') or '').strip().lower()
    volunteer = Volunteer.query.filter_by(instance_id=instance.id, email=email).first()

    if volunteer and not volunteer.is_deleted:
        raw_token = volunteer.generate_reset_token()
        db.session.commit()
        base_url = current_app.config.get('FRONTEND_URL', '')
        reset_url = f'{base_url}/{slug}/reset-password?token={raw_token}'
        try:
            send_mail(email, 'Passwort zurücksetzen',
                      build_reset_email(volunteer.name, reset_url, base_url))
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

    if not validate_password_strength(new_password):
        return jsonify(error='Passwort zu schwach (mind. 8 Zeichen, 1 Ziffer, 1 Sonderzeichen)'), 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    volunteer = Volunteer.query.filter_by(
        instance_id=instance.id, reset_token=token_hash
    ).first()

    if not volunteer or not volunteer.is_reset_token_valid or volunteer.is_deleted:
        return jsonify(error='Ungültiger oder abgelaufener Reset-Link'), 400

    volunteer.set_password(new_password)
    volunteer.clear_reset_token()
    db.session.commit()
    return jsonify(message='Passwort wurde geändert'), 200


def _build_instance_info(instance, settings, global_settings) -> dict:
    return {
        'slug': instance.slug,
        'name': instance.name,
        'title': settings.site_title if settings else instance.name,
        'primary_color': settings.primary_color if settings else '#4f46e5',
        'logo_filename': settings.logo_filename if settings else None,
        'site_locked': settings.site_locked if settings else False,
        'lock_message': settings.lock_message if settings else None,
        'shifts_enabled': settings.shifts_enabled if settings else True,
        'food_donations_enabled': settings.food_donations_enabled if settings else True,
        'registration_open': settings.registration_open if settings else True,
        'impressum_html': _merge_impressum(settings, global_settings),
        'privacy_policy_html': settings.privacy_policy_html if settings else None,
    }


def _merge_impressum(settings, global_settings) -> str:
    parts = []
    if global_settings and global_settings.provider_impressum_html:
        parts.append(global_settings.provider_impressum_html)
    if settings and settings.instance_impressum_html:
        parts.append(settings.instance_impressum_html)
    return '\n'.join(parts)
