from flask import request, g
from marshmallow import ValidationError

from . import admin_bp
from ...extensions import db
from ...models import Stand, ActivityLog
from ...schemas.shifts import StandSchema, StandCreateSchema, StandUpdateSchema, StandReorderSchema
from ...utils.auth import require_staff, require_instance_admin
from ...utils.responses import ok, created, no_content, error, optimistic_lock_conflict

_schema = StandSchema()
_many = StandSchema(many=True)
_create = StandCreateSchema()
_update = StandUpdateSchema()
_reorder = StandReorderSchema()


@admin_bp.route('/<slug>/stands', methods=['GET'])
@require_staff
def list_stands(slug):
    stands = Stand.query.filter_by(instance_id=g.instance.id).order_by(Stand.sort_order).all()
    return ok(_many.dump(stands))


@admin_bp.route('/<slug>/stands', methods=['POST'])
@require_instance_admin
def create_stand(slug):
    try:
        data = _create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    stand = Stand(instance_id=g.instance.id, **data)
    db.session.add(stand)
    _log(g.instance.id, f'Stand angelegt: {stand.name}', g.current_user)
    db.session.commit()
    return created(_schema.dump(stand))


@admin_bp.route('/<slug>/stands/<int:stand_id>', methods=['PUT'])
@require_instance_admin
def update_stand(slug, stand_id):
    stand = _get_or_404(stand_id, g.instance.id)
    raw = request.get_json() or {}
    try:
        data = _update.load(raw)
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    if optimistic_lock_conflict(stand, raw.get('updated_at')):
        return error('Datensatz wurde zwischenzeitlich geändert', 409)

    for key, value in data.items():
        setattr(stand, key, value)

    _log(g.instance.id, f'Stand geändert: {stand.name}', g.current_user)
    db.session.commit()
    return ok(_schema.dump(stand))


@admin_bp.route('/<slug>/stands/<int:stand_id>', methods=['DELETE'])
@require_instance_admin
def delete_stand(slug, stand_id):
    stand = _get_or_404(stand_id, g.instance.id)
    _log(g.instance.id, f'Stand gelöscht: {stand.name}', g.current_user)
    db.session.delete(stand)
    db.session.commit()
    return no_content()


@admin_bp.route('/<slug>/stands/reorder', methods=['PUT'])
@require_instance_admin
def reorder_stands(slug):
    try:
        data = _reorder.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    stands = {s.id: s for s in Stand.query.filter_by(instance_id=g.instance.id).all()}
    for position, stand_id in enumerate(data['order']):
        if stand_id in stands:
            stands[stand_id].sort_order = position

    db.session.commit()
    return ok(message='Reihenfolge gespeichert')


def _get_or_404(stand_id, instance_id):
    from flask import abort
    stand = Stand.query.filter_by(id=stand_id, instance_id=instance_id).first()
    if not stand:
        abort(404)
    return stand


def _log(instance_id, details, actor):
    db.session.add(ActivityLog(
        instance_id=instance_id,
        event_type=ActivityLog.AUDIT_DATA,
        volunteer_name=getattr(actor, 'email', str(actor)),
        actor_type=getattr(actor, 'role', 'admin'),
        ip_address=request.remote_addr,
        details=details,
    ))
