from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g, current_app
from flask_jwt_extended import create_access_token, create_refresh_token
from marshmallow import ValidationError

from ..extensions import db, limiter
from ..models import (
    Instance, SiteSettings, Stand, EventDate, Shift, Registration,
    FoodDonationType, FoodDonation, ActivityLog, Volunteer,
)
from ..schemas.shifts import ShiftSchema, RegistrationSchema
from ..schemas.food import FoodDonationSchema, FoodDonationCreateSchema
from ..utils.auth import require_volunteer
from ..utils.responses import ok, created, no_content, error

volunteer_bp = Blueprint('volunteer', __name__)

_shift_schema = ShiftSchema(many=True)
_reg_schema = RegistrationSchema(many=True)
_food_schema = FoodDonationSchema(many=True)
_food_create_schema = FoodDonationCreateSchema()


# ---------------------------------------------------------------------------
# Schichten
# ---------------------------------------------------------------------------

@volunteer_bp.route('/<slug>/shifts', methods=['GET'])
@require_volunteer
def list_shifts(slug):
    instance = g.instance
    settings = SiteSettings.query.filter_by(instance_id=instance.id).first()
    if settings and not settings.shifts_enabled:
        return error('Schichten sind deaktiviert', 403)

    dates = EventDate.query.filter_by(instance_id=instance.id).order_by(EventDate.date).all()
    result = []
    for date in dates:
        stands = Stand.query.filter_by(instance_id=instance.id).order_by(Stand.sort_order).all()
        for stand in stands:
            shifts = Shift.query.filter_by(
                stand_id=stand.id, event_date_id=date.id
            ).order_by(Shift.start_time).all()
            for shift in shifts:
                is_registered = Registration.query.filter_by(
                    volunteer_id=g.current_user.id, shift_id=shift.id
                ).first() is not None
                result.append({
                    **ShiftSchema().dump(shift),
                    'is_registered': is_registered,
                })
    return ok(result)


@volunteer_bp.route('/<slug>/shifts/<int:shift_id>/register', methods=['POST'])
@limiter.limit('30 per minute')
@require_volunteer
def register_shift(slug, shift_id):
    settings = SiteSettings.query.filter_by(instance_id=g.instance.id).first()
    if settings and not settings.registration_open:
        return error('Anmeldeschluss ist überschritten', 403)

    shift = _get_instance_shift(shift_id, g.instance.id)
    if not shift:
        return error('Schicht nicht gefunden', 404)
    if shift.is_full:
        return error('Schicht ist bereits voll', 409)

    if Registration.query.filter_by(volunteer_id=g.current_user.id, shift_id=shift_id).first():
        return error('Bereits eingetragen', 409)

    reg = Registration(volunteer_id=g.current_user.id, shift_id=shift_id)
    db.session.add(reg)
    db.session.add(_activity(g.instance.id, ActivityLog.SHIFT_REGISTER, g.current_user,
                             details=f'shift_id={shift_id}'))
    db.session.commit()
    return created({'shift_id': shift_id})


@volunteer_bp.route('/<slug>/shifts/<int:shift_id>/register', methods=['DELETE'])
@limiter.limit('30 per minute')
@require_volunteer
def unregister_shift(slug, shift_id):
    reg = Registration.query.filter_by(
        volunteer_id=g.current_user.id, shift_id=shift_id
    ).first()
    if not reg:
        return error('Nicht eingetragen', 404)

    db.session.delete(reg)
    db.session.add(_activity(g.instance.id, ActivityLog.SHIFT_UNREGISTER, g.current_user,
                             details=f'shift_id={shift_id}'))
    db.session.commit()
    return no_content()


@volunteer_bp.route('/<slug>/my-registrations', methods=['GET'])
@require_volunteer
def my_registrations(slug):
    regs = Registration.query.filter_by(volunteer_id=g.current_user.id).all()
    return ok(_reg_schema.dump(regs))


# ---------------------------------------------------------------------------
# Essensspenden
# ---------------------------------------------------------------------------

@volunteer_bp.route('/<slug>/food-donations', methods=['GET'])
@require_volunteer
def list_food_donations(slug):
    settings = SiteSettings.query.filter_by(instance_id=g.instance.id).first()
    if settings and not settings.food_donations_enabled:
        return error('Essensspenden sind deaktiviert', 403)

    donations = FoodDonation.query.filter_by(volunteer_id=g.current_user.id).all()
    return ok(_food_schema.dump(donations))


@volunteer_bp.route('/<slug>/food-donations', methods=['POST'])
@limiter.limit('20 per minute')
@require_volunteer
def create_food_donation(slug):
    settings = SiteSettings.query.filter_by(instance_id=g.instance.id).first()
    if settings and not settings.registration_open:
        return error('Anmeldeschluss ist überschritten', 403)

    try:
        data = _food_create_schema.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    food_type = FoodDonationType.query.filter_by(
        id=data['food_type_id'], instance_id=g.instance.id
    ).first()
    if not food_type:
        return error('Essenspendenart nicht gefunden', 404)

    donation = FoodDonation(volunteer_id=g.current_user.id, **data)
    db.session.add(donation)
    db.session.add(_activity(g.instance.id, ActivityLog.FOOD_REGISTER, g.current_user,
                             details=f'food_type_id={data["food_type_id"]}'))
    db.session.commit()
    return created(FoodDonationSchema().dump(donation))


@volunteer_bp.route('/<slug>/food-donations/<int:donation_id>', methods=['DELETE'])
@require_volunteer
def delete_food_donation(slug, donation_id):
    donation = FoodDonation.query.filter_by(
        id=donation_id, volunteer_id=g.current_user.id
    ).first()
    if not donation:
        return error('Essensspende nicht gefunden', 404)

    db.session.delete(donation)
    db.session.add(_activity(g.instance.id, ActivityLog.FOOD_UNREGISTER, g.current_user,
                             details=f'donation_id={donation_id}'))
    db.session.commit()
    return no_content()


# ---------------------------------------------------------------------------
# Profil + DSGVO
# ---------------------------------------------------------------------------

@volunteer_bp.route('/<slug>/profile', methods=['PUT'])
@require_volunteer
def update_profile(slug):
    from ..utils.auth import validate_password_strength
    data = request.get_json() or {}
    volunteer = g.current_user

    if 'name' in data:
        volunteer.name = data['name'].strip()
    if 'password' in data and data['password']:
        if not validate_password_strength(data['password']):
            return error('Passwort zu schwach', 400)
        volunteer.set_password(data['password'])

    db.session.commit()
    return ok({'name': volunteer.name, 'email': volunteer.email})


@volunteer_bp.route('/<slug>/profile', methods=['DELETE'])
@require_volunteer
def delete_profile(slug):
    volunteer = g.current_user
    volunteer.name = 'Gelöschter Nutzer'
    volunteer.email = None
    volunteer.password_hash = '!'
    volunteer.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    return no_content()


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _get_instance_shift(shift_id: int, instance_id: int):
    shift = Shift.query.get(shift_id)
    if not shift:
        return None
    stand = Stand.query.get(shift.stand_id)
    if not stand or stand.instance_id != instance_id:
        return None
    return shift


def _activity(instance_id, event_type, user, details=None) -> ActivityLog:
    return ActivityLog(
        instance_id=instance_id,
        event_type=event_type,
        volunteer_name=user.name,
        volunteer_id=user.id,
        ip_address=request.remote_addr,
        actor_type='volunteer',
        details=details,
        user_agent=request.headers.get('User-Agent', '')[:500],
    )
