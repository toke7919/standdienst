from flask import request, g
from marshmallow import Schema, fields, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from . import admin_bp
from ...extensions import db
from ...models import EventDate, Shift, ActivityLog
from ...schemas.shifts import EventDateSchema, EventDateCreateSchema, EventDateUpdateSchema
from ...utils.auth import require_staff, require_instance_admin
from ...utils.responses import ok, created, no_content, error, optimistic_lock_conflict

_schema = EventDateSchema()
_many = EventDateSchema(many=True)
_create = EventDateCreateSchema()
_update = EventDateUpdateSchema()


@admin_bp.route('/<slug>/dates', methods=['GET'])
@require_staff
def list_dates(slug):
    stmt = select(EventDate).filter_by(instance_id=g.instance.id).order_by(EventDate.date)
    if request.args.get('has_shifts', type=int):
        stmt = stmt.where(EventDate.shifts.any())
    if request.args.get('has_food_types', type=int):
        stmt = stmt.where(EventDate.food_types.any())
    return ok(_many.dump(db.session.scalars(stmt).all()))


@admin_bp.route('/<slug>/dates', methods=['POST'])
@require_instance_admin
def create_date(slug):
    try:
        data = _create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    event_date = EventDate(instance_id=g.instance.id, **data)
    db.session.add(event_date)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error('Datum bereits vorhanden', 409)

    _log(g.instance.id, f'Termin angelegt: {event_date.date}', g.current_user)
    db.session.commit()
    return created(_schema.dump(event_date))


@admin_bp.route('/<slug>/dates/<int:date_id>', methods=['PUT'])
@require_instance_admin
def update_date(slug, date_id):
    event_date = _get_or_404(date_id, g.instance.id)
    raw = request.get_json() or {}
    try:
        data = _update.load(raw)
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    if optimistic_lock_conflict(event_date, raw.get('updated_at')):
        return error('Datensatz wurde zwischenzeitlich geändert', 409)

    for key, value in data.items():
        setattr(event_date, key, value)

    _log(g.instance.id, f'Termin geändert: {event_date.date}', g.current_user)
    db.session.commit()
    return ok(_schema.dump(event_date))


@admin_bp.route('/<slug>/dates/<int:date_id>', methods=['DELETE'])
@require_instance_admin
def delete_date(slug, date_id):
    event_date = _get_or_404(date_id, g.instance.id)
    _log(g.instance.id, f'Termin gelöscht: {event_date.date}', g.current_user)
    db.session.delete(event_date)
    db.session.commit()
    return no_content()


class _DuplicateDateSchema(Schema):
    date = fields.Date(required=True)


_duplicate = _DuplicateDateSchema()


@admin_bp.route('/<slug>/dates/<int:date_id>/duplicate', methods=['POST'])
@require_instance_admin
def duplicate_date(slug, date_id):
    source = _get_or_404(date_id, g.instance.id)
    try:
        data = _duplicate.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    new_date = EventDate(
        instance_id=g.instance.id,
        date=data['date'],
        label=source.label,
        is_draft=True,
    )
    db.session.add(new_date)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return error('Datum bereits vorhanden', 409)

    source_shifts = db.session.scalars(select(Shift).filter_by(event_date_id=source.id)).all()
    for shift in source_shifts:
        db.session.add(Shift(
            stand_id=shift.stand_id,
            event_date_id=new_date.id,
            start_time=shift.start_time,
            end_time=shift.end_time,
            max_volunteers=shift.max_volunteers,
        ))

    _log(g.instance.id, f'Termin dupliziert: {source.date} → {new_date.date}', g.current_user)
    db.session.commit()
    return created(_schema.dump(new_date))


def _get_or_404(date_id, instance_id):
    from flask import abort
    date = db.session.scalars(select(EventDate).filter_by(id=date_id, instance_id=instance_id)).first()
    if not date:
        abort(404)
    return date


def _log(instance_id, details, actor):
    db.session.add(ActivityLog(
        instance_id=instance_id,
        event_type=ActivityLog.AUDIT_DATA,
        volunteer_name=getattr(actor, 'email', str(actor)),
        actor_type=getattr(actor, 'role', 'admin'),
        ip_address=request.remote_addr,
        details=details,
    ))
