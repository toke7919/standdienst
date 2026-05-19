from flask import request, g
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from . import admin_bp
from ...extensions import db
from ...models import Registration, Shift, Stand, Volunteer, ActivityLog
from ...schemas.shifts import RegistrationSchema, RegistrationCreateSchema
from ...utils.auth import require_staff, require_instance_admin
from ...utils.responses import ok, created, no_content, error, paginated

_schema = RegistrationSchema()
_many = RegistrationSchema(many=True)
_create = RegistrationCreateSchema()


@admin_bp.route('/<slug>/registrations', methods=['GET'])
@require_staff
def list_registrations(slug):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    shift_id = request.args.get('shift_id', type=int)
    date_id = request.args.get('date_id', type=int)

    q = (Registration.query
         .join(Shift, Registration.shift_id == Shift.id)
         .join(Stand, Shift.stand_id == Stand.id)
         .filter(Stand.instance_id == g.instance.id))

    if shift_id:
        q = q.filter(Registration.shift_id == shift_id)
    if date_id:
        q = q.filter(Shift.event_date_id == date_id)

    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False).items
    return paginated(_many.dump(items), total, page, per_page)


@admin_bp.route('/<slug>/registrations', methods=['POST'])
@require_instance_admin
def create_registration(slug):
    try:
        data = _create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    volunteer = Volunteer.query.filter_by(
        id=data['volunteer_id'], instance_id=g.instance.id
    ).first()
    shift = _get_instance_shift(data['shift_id'], g.instance.id)
    if not volunteer or not shift:
        return error('Helfer oder Schicht nicht gefunden', 404)
    if shift.is_full:
        return error('Schicht ist bereits voll', 409)
    if _has_time_overlap(volunteer.id, shift):
        return error('Helfer hat bereits eine überlappende Schicht an diesem Tag', 409)

    reg = Registration(registered_by_admin=True, **data)
    db.session.add(reg)
    db.session.add(ActivityLog(
        instance_id=g.instance.id,
        event_type=ActivityLog.AUDIT_DATA,
        volunteer_name=volunteer.name,
        actor_type=getattr(g.current_user, 'role', 'admin'),
        details=f'Admin-Eintragung: shift_id={data["shift_id"]}',
    ))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error('Helfer bereits in dieser Schicht eingetragen', 409)

    return created(_schema.dump(reg))


@admin_bp.route('/<slug>/registrations/<int:reg_id>', methods=['DELETE'])
@require_instance_admin
def delete_registration(slug, reg_id):
    reg = (Registration.query
           .join(Shift).join(Stand)
           .filter(Registration.id == reg_id, Stand.instance_id == g.instance.id)
           .first())
    if not reg:
        from flask import abort
        abort(404)

    db.session.delete(reg)
    db.session.commit()
    return no_content()


def _get_instance_shift(shift_id, instance_id):
    return (Shift.query
            .join(Stand, Shift.stand_id == Stand.id)
            .filter(Shift.id == shift_id, Stand.instance_id == instance_id)
            .first())


def _has_time_overlap(volunteer_id: int, new_shift: Shift) -> bool:
    existing = (
        Registration.query
        .join(Shift, Registration.shift_id == Shift.id)
        .filter(
            Registration.volunteer_id == volunteer_id,
            Shift.event_date_id == new_shift.event_date_id,
            Shift.id != new_shift.id,
        )
        .all()
    )
    return any(
        r.shift.start_time < new_shift.end_time and new_shift.start_time < r.shift.end_time
        for r in existing
    )
