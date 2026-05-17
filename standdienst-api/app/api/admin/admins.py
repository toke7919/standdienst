from flask import request, g
from marshmallow import ValidationError

from . import admin_bp
from ...extensions import db
from ...models import Admin, ActivityLog
from ...schemas.admin import AdminSchema, AdminCreateSchema, AdminUpdateSchema
from ...utils.auth import require_admin, validate_password_strength
from ...utils.responses import ok, created, no_content, error

_schema = AdminSchema()
_many = AdminSchema(many=True)
_create = AdminCreateSchema()
_update = AdminUpdateSchema()


@admin_bp.route('/admins', methods=['GET'])
@require_admin
def list_admins():
    admins = Admin.query.order_by(Admin.email).all()
    return ok(_many.dump(admins))


@admin_bp.route('/admins', methods=['POST'])
@require_admin
def create_admin():
    try:
        data = _create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    if Admin.query.filter_by(email=data['email'].lower()).first():
        return error('E-Mail-Adresse bereits vergeben', 409)
    if not validate_password_strength(data['password']):
        return error('Passwort zu schwach (mind. 8 Zeichen, 1 Ziffer, 1 Sonderzeichen)', 400)

    admin = Admin(email=data['email'].lower(), is_primary=data.get('is_primary', False))
    admin.set_password(data['password'])
    db.session.add(admin)
    _log(f'Admin angelegt: {admin.email}', g.current_user)
    db.session.commit()
    return created(_schema.dump(admin))


@admin_bp.route('/admins/<int:admin_id>', methods=['GET'])
@require_admin
def get_admin(admin_id):
    admin = Admin.query.get_or_404(admin_id)
    return ok(_schema.dump(admin))


@admin_bp.route('/admins/<int:admin_id>', methods=['PUT'])
@require_admin
def update_admin(admin_id):
    admin = Admin.query.get_or_404(admin_id)
    try:
        data = _update.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    if 'email' in data:
        email = data['email'].lower()
        existing = Admin.query.filter_by(email=email).first()
        if existing and existing.id != admin_id:
            return error('E-Mail-Adresse bereits vergeben', 409)
        admin.email = email
    if 'is_primary' in data:
        admin.is_primary = data['is_primary']
    if 'password' in data and data['password']:
        if not validate_password_strength(data['password']):
            return error('Passwort zu schwach', 400)
        admin.set_password(data['password'])

    _log(f'Admin geändert: {admin.email}', g.current_user)
    db.session.commit()
    return ok(_schema.dump(admin))


@admin_bp.route('/admins/<int:admin_id>', methods=['DELETE'])
@require_admin
def delete_admin(admin_id):
    admin = Admin.query.get_or_404(admin_id)
    if admin.id == g.current_user.id:
        return error('Eigenes Konto kann nicht gelöscht werden', 400)
    if Admin.query.count() <= 1:
        return error('Letzter Admin kann nicht gelöscht werden', 400)
    _log(f'Admin gelöscht: {admin.email}', g.current_user)
    db.session.delete(admin)
    db.session.commit()
    return no_content()


def _log(details, actor):
    db.session.add(ActivityLog(
        event_type=ActivityLog.AUDIT_ADMIN,
        volunteer_name=getattr(actor, 'email', str(actor)),
        actor_type='admin',
        details=details,
    ))
