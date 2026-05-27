from flask import request, g
from marshmallow import ValidationError
from sqlalchemy import select, delete

from . import admin_bp
from ...extensions import db
from ...models import (
    Instance, SiteSettings, ActivityLog,
    Volunteer, Stand, Shift, EventDate, Registration,
    FoodDonationType, FoodDonation,
)
from ...schemas.instance import InstanceSchema, InstanceCreateSchema, InstanceUpdateSchema
from ...utils.auth import require_admin, require_staff
from ...utils.responses import ok, created, no_content, error, paginated, clamp_pagination

_schema = InstanceSchema()
_many = InstanceSchema(many=True)
_create = InstanceCreateSchema()
_update = InstanceUpdateSchema()


@admin_bp.route('/instances', methods=['GET'])
@require_staff
def list_instances():
    page, per_page = clamp_pagination(
        request.args.get('page', 1, type=int),
        request.args.get('per_page', 20, type=int),
    )

    if g.role == 'organizer':
        instance_ids = [i.id for i in g.current_user.instances.all()]
        stmt = select(Instance).filter(Instance.id.in_(instance_ids)).order_by(Instance.name)
    else:
        stmt = select(Instance).order_by(Instance.name)

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    return paginated(_many.dump(pagination.items), pagination.total, page, per_page)


@admin_bp.route('/instances', methods=['POST'])
@require_admin
def create_instance():
    try:
        data = _create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    if db.session.scalars(select(Instance).filter_by(slug=data['slug'])).first():
        return error('Slug bereits vergeben', 409)

    instance = Instance(**data)
    db.session.add(instance)
    db.session.flush()

    settings = SiteSettings(instance_id=instance.id)
    db.session.add(settings)

    _log(instance.id, 'Instanz angelegt', g.current_user.email)
    db.session.commit()
    return created(_schema.dump(instance))


@admin_bp.route('/instances/<int:instance_id>', methods=['GET'])
@require_admin
def get_instance(instance_id):
    instance = db.get_or_404(Instance, instance_id)
    return ok(_schema.dump(instance))


@admin_bp.route('/instances/<int:instance_id>', methods=['PUT'])
@require_admin
def update_instance(instance_id):
    from ...utils.settings_cache import invalidate_site
    instance = db.get_or_404(Instance, instance_id)
    raw = request.get_json() or {}
    branding_enabled = raw.get('branding_enabled')
    try:
        data = _update.load(raw)
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    for key, value in data.items():
        setattr(instance, key, value)

    if branding_enabled is not None:
        settings = db.session.scalars(select(SiteSettings).filter_by(instance_id=instance_id)).first()
        if settings:
            settings.branding_enabled = bool(branding_enabled)
        invalidate_site(instance_id)

    _log(instance.id, 'Instanz geändert', g.current_user.email)
    db.session.commit()
    return ok(_schema.dump(instance))


@admin_bp.route('/instances/<int:instance_id>', methods=['DELETE'])
@require_admin
def delete_instance(instance_id):
    instance = db.get_or_404(Instance, instance_id)
    _log(None, f'Instanz gelöscht: {instance.name} (slug={instance.slug})', g.current_user.email)
    db.session.delete(instance)
    db.session.commit()
    return no_content()


@admin_bp.route('/<slug>/clear-data', methods=['DELETE'])
@require_staff
def clear_instance_data(slug):
    if g.role != 'admin':
        return error('Nur Admins können Instanzdaten löschen', 403)
    instance_id = g.instance.id

    stand_ids = select(Stand.id).filter_by(instance_id=instance_id)
    shift_ids = select(Shift.id).filter(Shift.stand_id.in_(stand_ids))
    ftype_ids = select(FoodDonationType.id).filter_by(instance_id=instance_id)

    db.session.execute(delete(Registration).filter(Registration.shift_id.in_(shift_ids)))
    db.session.execute(delete(FoodDonation).filter(FoodDonation.food_type_id.in_(ftype_ids)))
    db.session.execute(delete(FoodDonationType).filter_by(instance_id=instance_id))
    db.session.execute(delete(Shift).filter(Shift.stand_id.in_(stand_ids)))
    db.session.execute(delete(Stand).filter_by(instance_id=instance_id))
    db.session.execute(delete(EventDate).filter_by(instance_id=instance_id))
    db.session.execute(delete(Volunteer).filter_by(instance_id=instance_id))

    _log(instance_id, 'Alle Instanzdaten gelöscht', g.current_user.email)
    db.session.commit()
    return no_content()


def _log(instance_id, details, actor_email):
    db.session.add(ActivityLog(
        instance_id=instance_id,
        event_type=ActivityLog.AUDIT_DATA,
        volunteer_name=actor_email,
        actor_type='admin',
        ip_address=request.remote_addr,
        details=details,
    ))
