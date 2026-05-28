from flask import request, g
from marshmallow import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from . import admin_bp
from ...extensions import db
from ...models import EventDate, ActivityLog
from ...schemas.shifts import EventDateSchema, EventDateCreateSchema, EventDateUpdateSchema
from ...utils.auth import require_staff, require_instance_admin
from ...utils.responses import ok, created, no_content, error

_schema = EventDateSchema()
_many = EventDateSchema(many=True)
_create = EventDateCreateSchema()
_update = EventDateUpdateSchema()


@admin_bp.route('/<slug>/dates', methods=['GET'])
@require_staff
def list_dates(slug):
    dates = db.session.scalars(select(EventDate).filter_by(instance_id=g.instance.id).order_by(EventDate.date)).all()
    return ok(_many.dump(dates))


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
    try:
        data = _update.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

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
