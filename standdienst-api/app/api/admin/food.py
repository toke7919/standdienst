from flask import request, g
from marshmallow import ValidationError

from . import admin_bp
from ...extensions import db
from ...models import FoodDonationType, FoodDonation, ActivityLog, Volunteer, EventDate
from ...schemas.food import (
    FoodDonationTypeSchema, FoodDonationTypeCreateSchema, FoodDonationTypeUpdateSchema,
    FoodDonationSchema, FoodDonationAdminCreateSchema,
)
from ...utils.auth import require_staff, require_instance_admin
from ...utils.responses import ok, created, no_content, error, paginated

_type_schema = FoodDonationTypeSchema()
_type_many = FoodDonationTypeSchema(many=True)
_type_create = FoodDonationTypeCreateSchema()
_type_update = FoodDonationTypeUpdateSchema()
_don_schema = FoodDonationSchema()
_don_many = FoodDonationSchema(many=True)
_don_create = FoodDonationAdminCreateSchema()


# ---------------------------------------------------------------------------
# Essenspendenarten
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/food-types', methods=['GET'])
@require_staff
def list_food_types(slug):
    date_id = request.args.get('date_id', type=int)
    q = FoodDonationType.query.filter_by(instance_id=g.instance.id)
    if date_id:
        q = q.filter_by(event_date_id=date_id)
    return ok(_type_many.dump(q.order_by(FoodDonationType.name).all()))


@admin_bp.route('/<slug>/food-types', methods=['POST'])
@require_instance_admin
def create_food_type(slug):
    try:
        data = _type_create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    date = EventDate.query.filter_by(id=data['event_date_id'], instance_id=g.instance.id).first()
    if not date:
        return error('Termin nicht gefunden', 404)

    food_type = FoodDonationType(instance_id=g.instance.id, **data)
    db.session.add(food_type)
    db.session.commit()
    return created(_type_schema.dump(food_type))


@admin_bp.route('/<slug>/food-types/<int:type_id>', methods=['PUT'])
@require_instance_admin
def update_food_type(slug, type_id):
    food_type = FoodDonationType.query.filter_by(
        id=type_id, instance_id=g.instance.id
    ).first_or_404()
    try:
        data = _type_update.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    for key, value in data.items():
        setattr(food_type, key, value)

    db.session.commit()
    return ok(_type_schema.dump(food_type))


@admin_bp.route('/<slug>/food-types/<int:type_id>', methods=['DELETE'])
@require_instance_admin
def delete_food_type(slug, type_id):
    food_type = FoodDonationType.query.filter_by(
        id=type_id, instance_id=g.instance.id
    ).first_or_404()
    db.session.delete(food_type)
    db.session.commit()
    return no_content()


# ---------------------------------------------------------------------------
# Essensspenden
# ---------------------------------------------------------------------------

@admin_bp.route('/<slug>/food-donations', methods=['GET'])
@require_staff
def list_food_donations(slug):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    type_id = request.args.get('type_id', type=int)

    q = (FoodDonation.query
         .join(FoodDonationType)
         .filter(FoodDonationType.instance_id == g.instance.id))
    if type_id:
        q = q.filter(FoodDonation.food_type_id == type_id)

    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False).items
    return paginated(_don_many.dump(items), total, page, per_page)


@admin_bp.route('/<slug>/food-donations', methods=['POST'])
@require_instance_admin
def create_food_donation(slug):
    try:
        data = _don_create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    food_type = FoodDonationType.query.filter_by(
        id=data['food_type_id'], instance_id=g.instance.id
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
        details=f'{food_type.name}: {data["description"]} (Admin-Eintragung)',
    ))
    db.session.commit()
    return created(_don_schema.dump(donation))


@admin_bp.route('/<slug>/food-donations/<int:donation_id>', methods=['DELETE'])
@require_instance_admin
def delete_food_donation(slug, donation_id):
    donation = (FoodDonation.query
                .join(FoodDonationType)
                .filter(FoodDonation.id == donation_id,
                        FoodDonationType.instance_id == g.instance.id)
                .first_or_404())
    db.session.delete(donation)
    db.session.commit()
    return no_content()
