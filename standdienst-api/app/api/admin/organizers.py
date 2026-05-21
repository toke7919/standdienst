from flask import request, g
from marshmallow import ValidationError

from . import admin_bp
from ...extensions import db
from ...models import Organizer, Instance, ActivityLog
from ...models.instance import organizer_instances
from ...schemas.organizer import OrganizerSchema, OrganizerCreateSchema, OrganizerUpdateSchema
from ...utils.auth import require_admin, validate_password_strength
from ...utils.mail import is_mail_configured, send_mail, build_invite_email
from ...utils.responses import ok, created, no_content, error, paginated

_schema = OrganizerSchema()
_many = OrganizerSchema(many=True)
_create = OrganizerCreateSchema()
_update = OrganizerUpdateSchema()


@admin_bp.route('/organizers', methods=['GET'])
@require_admin
def list_organizers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    q = Organizer.query.order_by(Organizer.name)
    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False).items
    return paginated(_many.dump(items), total, page, per_page)


@admin_bp.route('/organizers', methods=['POST'])
@require_admin
def create_organizer():
    try:
        data = _create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    if Organizer.query.filter_by(email=data['email'].lower()).first():
        return error('E-Mail-Adresse bereits vergeben', 409)

    instance_ids = data.pop('instance_ids', [])
    password = data.pop('password', None)

    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    full_name = f'{first_name} {last_name}'.strip()
    organizer = Organizer(
        email=data['email'].lower(),
        first_name=first_name,
        last_name=last_name,
        name=full_name or first_name,
        is_instance_admin=data.get('is_instance_admin', False),
    )
    if password:
        if not validate_password_strength(password):
            return error('Passwort zu schwach', 400)
        organizer.set_password(password)

    db.session.add(organizer)
    db.session.flush()
    _assign_instances(organizer, instance_ids)

    _log(f'Organisator angelegt: {organizer.email}', g.current_user)
    db.session.commit()

    if is_mail_configured():
        try:
            from ..public import _base_url
            base_url = _base_url()
            login_url = f'{base_url}/admin/login'
            send_mail(organizer.email, 'Dein Organisator-Konto bei Standdienst',
                      build_invite_email(organizer.name or organizer.email, 'Organisator', login_url, base_url))
        except Exception:
            pass

    return created(_schema.dump(organizer))


@admin_bp.route('/organizers/<int:organizer_id>', methods=['GET'])
@require_admin
def get_organizer(organizer_id):
    organizer = Organizer.query.get_or_404(organizer_id)
    return ok(_schema.dump(organizer))


@admin_bp.route('/organizers/<int:organizer_id>', methods=['PUT'])
@require_admin
def update_organizer(organizer_id):
    organizer = Organizer.query.get_or_404(organizer_id)
    try:
        data = _update.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    if 'email' in data:
        email = data['email'].lower()
        existing = Organizer.query.filter_by(email=email).first()
        if existing and existing.id != organizer_id:
            return error('E-Mail-Adresse bereits vergeben', 409)
        organizer.email = email
    if 'first_name' in data or 'last_name' in data:
        organizer.first_name = data.get('first_name', organizer.first_name or '').strip()
        organizer.last_name = data.get('last_name', organizer.last_name or '').strip()
        organizer.name = f'{organizer.first_name} {organizer.last_name}'.strip() or organizer.first_name
    if 'is_instance_admin' in data:
        organizer.is_instance_admin = data['is_instance_admin']
    if 'password' in data and data['password']:
        if not validate_password_strength(data['password']):
            return error('Passwort zu schwach', 400)
        organizer.set_password(data['password'])
    if 'instance_ids' in data:
        _assign_instances(organizer, data['instance_ids'])

    _log(f'Organisator geändert: {organizer.email}', g.current_user)
    db.session.commit()
    return ok(_schema.dump(organizer))


@admin_bp.route('/organizers/<int:organizer_id>', methods=['DELETE'])
@require_admin
def delete_organizer(organizer_id):
    organizer = Organizer.query.get_or_404(organizer_id)
    _log(f'Organisator gelöscht: {organizer.email}', g.current_user)
    db.session.delete(organizer)
    db.session.commit()
    return no_content()


def _assign_instances(organizer, instance_ids: list):
    db.session.execute(
        organizer_instances.delete().where(
            organizer_instances.c.organizer_id == organizer.id
        )
    )
    for iid in instance_ids:
        instance = Instance.query.get(iid)
        if instance:
            db.session.execute(
                organizer_instances.insert().values(
                    organizer_id=organizer.id,
                    instance_id=iid,
                    is_primary=(iid == instance_ids[0]),
                )
            )


def _log(details, actor):
    db.session.add(ActivityLog(
        event_type=ActivityLog.AUDIT_ORGANIZER,
        volunteer_name=getattr(actor, 'email', str(actor)),
        actor_type='admin',
        details=details,
    ))
