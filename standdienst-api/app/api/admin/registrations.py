from collections import defaultdict

from flask import request, g
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from . import admin_bp
from ...extensions import db
from ...models import Registration, Shift, Stand, EventDate, ActivityLog, Volunteer
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


@admin_bp.route('/<slug>/registrations/grid', methods=['GET'])
@require_staff
def registration_grid(slug):
    """Gibt alle Dienste + Anmeldungen als tabellarische Grid-Struktur zurück.
    Struktur: eine Sektion pro Veranstaltungstag, Stände als Spalten, Zeiten als Zeilen.
    """
    # Alle Dienste dieser Instanz mit Stand und Datum laden
    shifts = (Shift.query
              .join(Stand, Shift.stand_id == Stand.id)
              .join(EventDate, Shift.event_date_id == EventDate.id)
              .filter(Stand.instance_id == g.instance.id)
              .order_by(EventDate.date, Stand.sort_order, Shift.start_time)
              .all())

    if not shifts:
        return ok([])

    # Alle Anmeldungen für diese Dienste laden
    shift_ids = [s.id for s in shifts]
    registrations = Registration.query.filter(Registration.shift_id.in_(shift_ids)).all()

    # Anmeldungen nach shift_id gruppieren
    regs_by_shift: dict[int, list] = defaultdict(list)
    for reg in registrations:
        name = reg.volunteer.name if reg.volunteer else reg.guest_name or '—'
        regs_by_shift[reg.shift_id].append({
            'id': reg.id,
            'name': name,
            'by_admin': bool(reg.registered_by_admin),
        })

    # Daten für Grid aufbauen
    # Gruppierung: date_id → stand_id → time_range → shift
    dates_seen: dict[int, dict] = {}  # date_id → {meta, stands, time_slots}
    stands_per_date: dict[int, dict] = defaultdict(dict)  # date_id → {stand_id: stand}
    slots_per_date: dict[int, set] = defaultdict(set)     # date_id → {(start, end)}
    shift_map: dict[int, dict[int, object]] = defaultdict(dict)  # date_id → {(start,end): {stand_id: shift}}

    for shift in shifts:
        date_id = shift.event_date_id
        stand_id = shift.stand_id
        slot = (shift.start_time, shift.end_time)

        if date_id not in dates_seen:
            dates_seen[date_id] = {
                'date_id': date_id,
                'date_formatted': shift.event_date.formatted,
                'date_sort': shift.event_date.date,
            }
        stands_per_date[date_id][stand_id] = shift.stand
        slots_per_date[date_id].add(slot)

        if slot not in shift_map[date_id]:
            shift_map[date_id][slot] = {}
        shift_map[date_id][slot][stand_id] = shift

    # Grid-Struktur serialisieren
    result = []
    for date_id, date_meta in sorted(dates_seen.items(), key=lambda x: x[1]['date_sort']):
        stands = sorted(stands_per_date[date_id].values(), key=lambda s: (s.sort_order, s.name))
        slots = sorted(slots_per_date[date_id])

        rows = []
        for (start, end) in slots:
            cells = []
            slot_shifts = shift_map[date_id].get((start, end), {})
            for stand in stands:
                shift = slot_shifts.get(stand.id)
                if shift is None:
                    cells.append(None)
                else:
                    cells.append({
                        'shift_id': shift.id,
                        'max_volunteers': shift.max_volunteers,
                        'spots_left': shift.spots_left,
                        'registrations': regs_by_shift[shift.id],
                    })
            rows.append({
                'time_range': f'{start.strftime("%H:%M")} – {end.strftime("%H:%M")}',
                'cells': cells,
            })

        result.append({
            'date_id': date_meta['date_id'],
            'date_formatted': date_meta['date_formatted'],
            'stands': [{'id': s.id, 'name': s.name} for s in stands],
            'rows': rows,
        })

    return ok(result)


@admin_bp.route('/<slug>/registrations', methods=['POST'])
@require_instance_admin
def create_registration(slug):
    try:
        data = _create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    volunteer_id = data.get('volunteer_id')
    guest_name = data.get('guest_name')
    if not volunteer_id and not guest_name:
        return error('Name oder Helfer-ID erforderlich', 422)

    shift = _get_instance_shift(data['shift_id'], g.instance.id)
    if not shift:
        return error('Dienst nicht gefunden', 404)
    if shift.is_full:
        return error('Dienst ist bereits voll', 409)

    volunteer = None
    if volunteer_id:
        volunteer = Volunteer.query.filter_by(id=volunteer_id, instance_id=g.instance.id).first()
        if not volunteer:
            return error('Helfer nicht gefunden', 404)
        if volunteer.deleted_at:
            return error('Helfer ist pseudonymisiert', 400)

    display_name = volunteer.display_name if volunteer else guest_name
    stand     = shift.stand
    date      = shift.event_date
    time_str  = f'{shift.start_time.strftime("%H:%M")}–{shift.end_time.strftime("%H:%M")}'
    detail    = f'{stand.name} · {date.date.strftime("%d.%m.%Y")} · {time_str} (Admin-Eintragung)'

    reg = Registration(
        shift_id=data['shift_id'],
        guest_name=None if volunteer else guest_name,
        volunteer_id=volunteer_id,
        registered_by_admin=True,
    )
    db.session.add(reg)
    db.session.add(ActivityLog(
        instance_id=g.instance.id,
        event_type=ActivityLog.SHIFT_REGISTER,
        volunteer_name=display_name,
        actor_type=getattr(g.current_user, 'role', 'admin'),
        ip_address=request.remote_addr,
        details=detail,
    ))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error('Eintragung fehlgeschlagen', 409)

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

    shift     = reg.shift
    stand     = shift.stand
    date      = shift.event_date
    time_str  = f'{shift.start_time.strftime("%H:%M")}–{shift.end_time.strftime("%H:%M")}'
    name      = reg.volunteer.name if reg.volunteer else reg.guest_name or '—'
    detail    = f'{stand.name} · {date.date.strftime("%d.%m.%Y")} · {time_str}'

    db.session.delete(reg)
    db.session.add(ActivityLog(
        instance_id=g.instance.id,
        event_type=ActivityLog.SHIFT_UNREGISTER,
        volunteer_name=name,
        actor_type=getattr(g.current_user, 'role', 'admin'),
        ip_address=request.remote_addr,
        details=detail + ' (Admin-Abmeldung)',
    ))
    db.session.commit()
    return no_content()


def _get_instance_shift(shift_id, instance_id):
    return (Shift.query
            .join(Stand, Shift.stand_id == Stand.id)
            .filter(Shift.id == shift_id, Stand.instance_id == instance_id)
            .first())
