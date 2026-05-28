from flask import request, g
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from . import admin_bp
from ...extensions import db
from ...models import Shift, Stand, EventDate, ActivityLog
from ...schemas.shifts import ShiftSchema, ShiftCreateSchema, ShiftUpdateSchema
from ...utils.auth import require_staff, require_instance_admin
from ...utils.responses import ok, created, no_content, error, optimistic_lock_conflict

_schema = ShiftSchema()
_many = ShiftSchema(many=True)
_create = ShiftCreateSchema()
_update = ShiftUpdateSchema()


@admin_bp.route('/<slug>/shifts', methods=['GET'])
@require_staff
def list_shifts(slug):
    date_id = request.args.get('date_id', type=int)
    stand_id = request.args.get('stand_id', type=int)

    q = (Shift.query
         .join(Stand, Shift.stand_id == Stand.id)
         .filter(Stand.instance_id == g.instance.id))
    if date_id:
        q = q.filter(Shift.event_date_id == date_id)
    if stand_id:
        q = q.filter(Shift.stand_id == stand_id)

    shifts = q.order_by(Shift.event_date_id, Shift.start_time).all()
    return ok(_many.dump(shifts))


@admin_bp.route('/<slug>/shifts', methods=['POST'])
@require_instance_admin
def create_shift(slug):
    try:
        data = _create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    if data['start_time'] >= data['end_time']:
        return error('Startzeit muss vor der Endzeit liegen', 400)

    stand = Stand.query.filter_by(id=data['stand_id'], instance_id=g.instance.id).first()
    date = EventDate.query.filter_by(id=data['event_date_id'], instance_id=g.instance.id).first()
    if not stand or not date:
        return error('Stand oder Termin nicht gefunden', 404)

    shift = Shift(**data)
    db.session.add(shift)
    start_str = data['start_time'].strftime('%H:%M')
    end_str = data['end_time'].strftime('%H:%M')
    _log(g.instance.id, f'Dienst angelegt: {stand.name} am {date.formatted}, {start_str}–{end_str}', g.current_user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error('Dienst mit diesen Parametern existiert bereits', 409)
    shift = _get_or_404(shift.id, g.instance.id)
    return created(_schema.dump(shift))


@admin_bp.route('/<slug>/shifts/<int:shift_id>', methods=['PUT'])
@require_instance_admin
def update_shift(slug, shift_id):
    shift = _get_or_404(shift_id, g.instance.id)
    raw = request.get_json() or {}
    try:
        data = _update.load(raw)
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    start = data.get('start_time', shift.start_time)
    end = data.get('end_time', shift.end_time)
    if start >= end:
        return error('Startzeit muss vor der Endzeit liegen', 400)

    if optimistic_lock_conflict(shift, raw.get('updated_at')):
        return error('Datensatz wurde zwischenzeitlich geändert', 409)

    for key, value in data.items():
        setattr(shift, key, value)

    stand_name = shift.stand.name if shift.stand else f'Stand {shift.stand_id}'
    date_fmt = shift.event_date.formatted if shift.event_date else ''
    _log(g.instance.id, f'Dienst geändert: {stand_name} am {date_fmt}, {shift.time_range}', g.current_user)
    db.session.commit()
    return ok(_schema.dump(shift))


@admin_bp.route('/<slug>/shifts/<int:shift_id>', methods=['DELETE'])
@require_instance_admin
def delete_shift(slug, shift_id):
    shift = _get_or_404(shift_id, g.instance.id)
    stand_name = shift.stand.name if shift.stand else f'Stand {shift.stand_id}'
    date_fmt = shift.event_date.formatted if shift.event_date else ''
    _log(g.instance.id, f'Dienst gelöscht: {stand_name} am {date_fmt}, {shift.time_range}', g.current_user)
    db.session.delete(shift)
    db.session.commit()
    return no_content()


def _get_or_404(shift_id, instance_id):
    from flask import abort
    shift = (Shift.query
             .join(Stand, Shift.stand_id == Stand.id)
             .filter(Shift.id == shift_id, Stand.instance_id == instance_id)
             .first())
    if not shift:
        abort(404)
    return shift


def _log(instance_id, details, actor):
    db.session.add(ActivityLog(
        instance_id=instance_id,
        event_type=ActivityLog.AUDIT_DATA,
        volunteer_name=getattr(actor, 'email', str(actor)),
        actor_type=getattr(actor, 'role', 'admin'),
        ip_address=request.remote_addr,
        details=details,
    ))
