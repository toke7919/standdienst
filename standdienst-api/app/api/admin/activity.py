from flask import request, g
from sqlalchemy import select, func

from . import admin_bp
from ...extensions import db
from ...models import ActivityLog, Instance
from ...utils.auth import require_admin, require_instance_admin
from ...utils.responses import paginated, clamp_pagination

_SORT_COLUMNS = {
    'timestamp':      ActivityLog.timestamp,
    'event_type':     ActivityLog.event_type,
    'volunteer_name': ActivityLog.volunteer_name,
}


def _apply_sort(stmt, sort_param, dir_param):
    col = _SORT_COLUMNS.get(sort_param, ActivityLog.timestamp)
    return stmt.order_by(col.asc() if dir_param == 'asc' else col.desc())


def _apply_type_filter(stmt, raw: str | None):
    if not raw:
        return stmt
    types = [t.strip() for t in raw.split(',') if t.strip()]
    if types:
        stmt = stmt.filter(ActivityLog.event_type.in_(types))
    return stmt


def _serialize(entry, include_ip: bool = True, instance_map: dict | None = None) -> dict:
    inst = instance_map.get(entry.instance_id) if instance_map and entry.instance_id else None
    d = {
        'id': entry.id,
        'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
        'event_type': entry.event_type,
        'volunteer_name': entry.volunteer_name,
        'details': entry.details,
        'actor_type': entry.actor_type,
        'instance_id': entry.instance_id,
        'instance_name': inst.name if inst else None,
        'instance_slug': inst.slug if inst else None,
    }
    if include_ip:
        d['ip_address'] = entry.ip_address
    return d


@admin_bp.route('/activity', methods=['GET'])
@require_admin
def global_activity():
    page, per_page = clamp_pagination(
        request.args.get('page', 1, type=int),
        request.args.get('per_page', 50, type=int),
    )
    sort        = request.args.get('sort', 'timestamp')
    direction   = request.args.get('dir', 'desc')
    event_types = request.args.get('event_types')
    instance_id = request.args.get('instance_id', type=int)

    stmt = select(ActivityLog)
    if instance_id is not None:
        stmt = stmt.filter(ActivityLog.instance_id == instance_id)
    stmt = _apply_type_filter(stmt, event_types)
    stmt = _apply_sort(stmt, sort, direction)

    total = db.session.scalar(
        select(func.count()).select_from(
            stmt.order_by(None).subquery()
        )
    )
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    items = pagination.items

    # Instanznamen einmalig laden
    inst_ids = {e.instance_id for e in items if e.instance_id}
    inst_map = {i.id: i for i in db.session.scalars(select(Instance).filter(Instance.id.in_(inst_ids))).all()} if inst_ids else {}

    return paginated([_serialize(e, include_ip=True, instance_map=inst_map) for e in items],
                     total, page, per_page)


@admin_bp.route('/<slug>/activity', methods=['GET'])
@require_instance_admin
def instance_activity(slug):
    page, per_page = clamp_pagination(
        request.args.get('page', 1, type=int),
        request.args.get('per_page', 50, type=int),
    )
    sort        = request.args.get('sort', 'timestamp')
    direction   = request.args.get('dir', 'desc')
    event_types = request.args.get('event_types')

    stmt = select(ActivityLog).filter_by(instance_id=g.instance.id)
    stmt = _apply_type_filter(stmt, event_types)
    stmt = _apply_sort(stmt, sort, direction)

    total = db.session.scalar(
        select(func.count()).select_from(
            stmt.order_by(None).subquery()
        )
    )
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    items = pagination.items
    return paginated([_serialize(e, include_ip=False) for e in items], total, page, per_page)
