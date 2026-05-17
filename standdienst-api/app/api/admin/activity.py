from flask import request, g

from . import admin_bp
from ...models import ActivityLog
from ...schemas.activity import ActivityLogSchema
from ...utils.auth import require_admin, require_staff
from ...utils.responses import paginated

_many = ActivityLogSchema(many=True)


@admin_bp.route('/activity', methods=['GET'])
@require_admin
def global_activity():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    event_type = request.args.get('event_type')

    q = ActivityLog.query.filter(ActivityLog.instance_id.is_(None))
    if event_type:
        q = q.filter_by(event_type=event_type)

    q = q.order_by(ActivityLog.timestamp.desc())
    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False).items
    return paginated(_many.dump(items), total, page, per_page)


@admin_bp.route('/<slug>/activity', methods=['GET'])
@require_staff
def instance_activity(slug):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    event_type = request.args.get('event_type')

    q = ActivityLog.query.filter_by(instance_id=g.instance.id)
    if event_type:
        q = q.filter_by(event_type=event_type)

    q = q.order_by(ActivityLog.timestamp.desc())
    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False).items
    return paginated(_many.dump(items), total, page, per_page)
