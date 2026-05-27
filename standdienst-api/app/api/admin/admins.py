from flask import request, g
from marshmallow import ValidationError

from . import admin_bp
from ...extensions import db
from ...models import Admin, ActivityLog
from ...schemas.admin import AdminSchema, AdminCreateSchema, AdminUpdateSchema
from ...utils.auth import require_admin, validate_password_strength
from ...utils.mail import is_mail_configured, send_mail, build_invite_email
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

    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    full_name = f'{first_name} {last_name}'.strip()
    admin = Admin(
        email=data['email'].lower(),
        is_primary=data.get('is_primary', False),
        first_name=first_name,
        last_name=last_name,
        name=full_name,
    )
    admin.set_password(data['password'])
    db.session.add(admin)
    _log(f'Admin angelegt: {admin.email}', g.current_user)
    db.session.commit()

    if is_mail_configured():
        try:
            from ..public import _base_url
            base_url = _base_url()
            login_url = f'{base_url}/admin/login'
            send_mail(admin.email, 'Dein Admin-Konto bei Standdienst',
                      build_invite_email(admin.name or admin.email, 'Administrator', login_url, base_url))
        except Exception:
            pass

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

    if 'first_name' in data or 'last_name' in data:
        admin.first_name = data.get('first_name', admin.first_name or '').strip()
        admin.last_name = data.get('last_name', admin.last_name or '').strip()
        admin.name = f'{admin.first_name} {admin.last_name}'.strip()
    if 'email' in data:
        email = data['email'].lower()
        existing = Admin.query.filter_by(email=email).first()
        if existing and existing.id != admin_id:
            return error('E-Mail-Adresse bereits vergeben', 409)
        admin.email = email
    if 'is_primary' in data:
        new_primary = data['is_primary']
        if new_primary and not admin.is_primary:
            # Alle bisherigen Primaries abwählen
            for old in Admin.query.filter_by(is_primary=True).all():
                if old.id != admin_id:
                    old.is_primary = False
            admin.is_primary = True
        elif not new_primary and admin.is_primary:
            # Letzten Primary schützen
            if Admin.query.filter_by(is_primary=True).count() <= 1:
                return error('Letzter primärer Admin kann nicht abgewählt werden', 400)
            admin.is_primary = False
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
    if admin.is_primary:
        return error('Primärer Admin kann nicht gelöscht werden', 400)
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
        ip_address=request.remote_addr,
        details=details,
    ))
