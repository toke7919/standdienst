from flask import request
from . import admin_bp
from ...extensions import db
from ...models import GlobalSettings
from ...utils.auth import require_admin
from ...utils.responses import ok, error


@admin_bp.route('/maintenance', methods=['PUT'])
@require_admin
def set_maintenance_mode():
    enabled = request.get_json(force=True, silent=True) or {}
    if 'enabled' not in enabled:
        return error('Feld "enabled" fehlt', 400)
    mode = bool(enabled['enabled'])
    gs = GlobalSettings.query.first()
    if not gs:
        return error('GlobalSettings nicht gefunden', 500)
    gs.maintenance_mode = mode
    db.session.commit()
    return ok({'maintenance_mode': mode})
