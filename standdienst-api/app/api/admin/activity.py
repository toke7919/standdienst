from flask import request, g

from . import admin_bp
from ...models import ActivityLog
from ...schemas.activity import ActivityLogSchema
from ...utils.auth import require_admin, require_staff
from ...utils.responses import paginated

_many = ActivityLogSchema(many=True)

_SORT_COLUMNS = {
    'timestamp': ActivityLog.timestamp,
    'event_type': ActivityLog.event_type,
    'volunteer_name': ActivityLog.volunteer_name,
}


def _apply_sort(q, sort_param, dir_param):
    col = _SORT_COLUMNS.get(sort_param, ActivityLog.timestamp)
    return q.order_by(col.asc() if dir_param == 'asc' else col.desc())


def _apply_type_filter(q, raw: str | None):
    """Filtert nach einem oder mehreren kommaseparierten event_types."""
    if not raw:
        return q
    types = [t.strip() for t in raw.split(',') if t.strip()]
    if types:
        q = q.filter(ActivityLog.event_type.in_(types))
    return q


@admin_bp.route('/activity', methods=['GET'])
@require_admin
def global_activity():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    sort = request.args.get('sort', 'timestamp')
    direction = request.args.get('dir', 'desc')
    event_types = request.args.get('event_types')

    q = ActivityLog.query.filter(ActivityLog.instance_id.is_(None))
    q = _apply_type_filter(q, event_types)
    q = _apply_sort(q, sort, direction)
    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False).items
    return paginated(_many.dump(items), total, page, per_page)


@admin_bp.route('/<slug>/activity', methods=['GET'])
@require_staff
def instance_activity(slug):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    sort = request.args.get('sort', 'timestamp')
    direction = request.args.get('dir', 'desc')
    event_types = request.args.get('event_types')

    q = ActivityLog.query.filter_by(instance_id=g.instance.id)
    q = _apply_type_filter(q, event_types)
    q = _apply_sort(q, sort, direction)
    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False).items
    return paginated(_many.dump(items), total, page, per_page)
