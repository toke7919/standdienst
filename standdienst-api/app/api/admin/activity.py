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


@admin_bp.route('/activity', methods=['GET'])
@require_admin
def global_activity():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    event_type = request.args.get('event_type')
    sort = request.args.get('sort', 'timestamp')
    direction = request.args.get('dir', 'desc')

    q = ActivityLog.query.filter(ActivityLog.instance_id.is_(None))
    if event_type:
        q = q.filter_by(event_type=event_type)

    q = _apply_sort(q, sort, direction)
    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False).items
    return paginated(_many.dump(items), total, page, per_page)


@admin_bp.route('/<slug>/activity', methods=['GET'])
@require_staff
def instance_activity(slug):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    event_type = request.args.get('event_type')
    sort = request.args.get('sort', 'timestamp')
    direction = request.args.get('dir', 'desc')

    q = ActivityLog.query.filter_by(instance_id=g.instance.id)
    if event_type:
        q = q.filter_by(event_type=event_type)

    q = _apply_sort(q, sort, direction)
    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False).items
    return paginated(_many.dump(items), total, page, per_page)
