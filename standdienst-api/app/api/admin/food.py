from flask import request, g
from marshmallow import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import contains_eager

from . import admin_bp
from ...extensions import db
from ...models import FoodDonationType, FoodDonation, ActivityLog, Volunteer, EventDate
from ...schemas.food import (
    FoodDonationTypeSchema, FoodDonationTypeCreateSchema, FoodDonationTypeUpdateSchema,
    FoodDonationSchema, FoodDonationAdminCreateSchema, FoodDonationAdminUpdateSchema,
)
from ...utils.auth import require_staff, require_instance_admin
from ...utils.responses import ok, created, no_content, error, paginated, clamp_pagination, optimistic_lock_conflict

_type_schema = FoodDonationTypeSchema()
_type_many = FoodDonationTypeSchema(many=True)
_type_create = FoodDonationTypeCreateSchema()
_type_update = FoodDonationTypeUpdateSchema()
_don_schema = FoodDonationSchema()
_don_many = FoodDonationSchema(many=True)
_don_create = FoodDonationAdminCreateSchema()
_don_update = FoodDonationAdminUpdateSchema()


# ---------------------------------------------------------------------------
# Essenspendenarten
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/food-types', methods=['GET'])
@require_staff
def list_food_types(slug):
    date_id = request.args.get('date_id', type=int)
    stmt = (
        select(FoodDonationType)
        .filter_by(instance_id=g.instance.id)
        .join(FoodDonationType.event_date)
        .options(contains_eager(FoodDonationType.event_date))
    )
    if date_id:
        stmt = stmt.filter(FoodDonationType.event_date_id == date_id)
    stmt = stmt.order_by(EventDate.date, FoodDonationType.name)
    return ok(_type_many.dump(db.session.scalars(stmt).all()))


@admin_bp.route('/<slug>/food-types', methods=['POST'])
@require_instance_admin
def create_food_type(slug):
    try:
        data = _type_create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    date = db.session.scalars(select(EventDate).filter_by(id=data['event_date_id'], instance_id=g.instance.id)).first()
    if not date:
        return error('Termin nicht gefunden', 404)

    food_type = FoodDonationType(instance_id=g.instance.id, **data)
    db.session.add(food_type)
    db.session.commit()
    return created(_type_schema.dump(food_type))


@admin_bp.route('/<slug>/food-types/<int:type_id>', methods=['PUT'])
@require_instance_admin
def update_food_type(slug, type_id):
    food_type = db.first_or_404(
        select(FoodDonationType).filter_by(id=type_id, instance_id=g.instance.id)
    )
    raw = request.get_json() or {}
    try:
        data = _type_update.load(raw)
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    if optimistic_lock_conflict(food_type, raw.get('updated_at')):
        return error('Datensatz wurde zwischenzeitlich geändert', 409)

    for key, value in data.items():
        setattr(food_type, key, value)

    db.session.commit()
    return ok(_type_schema.dump(food_type))


@admin_bp.route('/<slug>/food-types/<int:type_id>', methods=['DELETE'])
@require_instance_admin
def delete_food_type(slug, type_id):
    food_type = db.first_or_404(
        select(FoodDonationType).filter_by(id=type_id, instance_id=g.instance.id)
    )
    db.session.delete(food_type)
    db.session.commit()
    return no_content()


# ---------------------------------------------------------------------------
# Essensspenden
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/food-donations', methods=['GET'])
@require_staff
def list_food_donations(slug):
    page, per_page = clamp_pagination(
        request.args.get('page', 1, type=int),
        request.args.get('per_page', 50, type=int),
    )
    type_id = request.args.get('type_id', type=int)

    stmt = (select(FoodDonation)
            .join(FoodDonationType)
            .where(FoodDonationType.instance_id == g.instance.id))
    if type_id:
        stmt = stmt.where(FoodDonation.food_type_id == type_id)

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    return paginated(_don_many.dump(pagination.items), pagination.total, page, per_page)


@admin_bp.route('/<slug>/food-donations', methods=['POST'])
@require_instance_admin
def create_food_donation(slug):
    try:
        data = _don_create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    food_type = db.session.scalars(
        select(FoodDonationType).filter_by(id=data['food_type_id'], instance_id=g.instance.id)
    ).first()
    if not food_type:
        return error('Essenspendenart nicht gefunden', 404)

    donation = FoodDonation(
        volunteer_id=None,
        guest_name=data['guest_name'],
        food_type_id=data['food_type_id'],
        description=data['description'],
        needs_refrigeration=data.get('needs_refrigeration', False),
    )
    db.session.add(donation)
    db.session.add(ActivityLog(
        instance_id=g.instance.id,
        event_type=ActivityLog.FOOD_REGISTER,
        volunteer_name=data['guest_name'],
        actor_type=getattr(g.current_user, 'role', 'admin'),
        ip_address=request.remote_addr,
        details=f'{food_type.name}: {data["description"]} (Admin-Eintragung)',
    ))
    db.session.commit()
    return created(_don_schema.dump(donation))


@admin_bp.route('/<slug>/food-donations/<int:donation_id>', methods=['PUT'])
@require_instance_admin
def update_food_donation(slug, donation_id):
    donation = db.first_or_404(
        select(FoodDonation)
        .join(FoodDonationType)
        .where(FoodDonation.id == donation_id,
               FoodDonationType.instance_id == g.instance.id)
    )
    try:
        data = _don_update.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    for key, value in data.items():
        setattr(donation, key, value)

    db.session.commit()
    return ok(_don_schema.dump(donation))


@admin_bp.route('/<slug>/food-donations/<int:donation_id>', methods=['DELETE'])
@require_instance_admin
def delete_food_donation(slug, donation_id):
    donation = db.first_or_404(
        select(FoodDonation)
        .join(FoodDonationType)
        .where(FoodDonation.id == donation_id,
               FoodDonationType.instance_id == g.instance.id)
    )
    db.session.delete(donation)
    db.session.commit()
    return no_content()
