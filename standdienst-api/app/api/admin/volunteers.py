from flask import request, g
from marshmallow import ValidationError

from . import admin_bp
from ...extensions import db
from ...models import Volunteer, ActivityLog
from ...schemas.volunteer import VolunteerSchema, VolunteerCreateSchema, VolunteerUpdateSchema
from ...utils.auth import require_admin, require_staff, require_instance_admin, validate_password_strength
from ...utils.responses import ok, created, no_content, error, paginated

_schema = VolunteerSchema()
_many = VolunteerSchema(many=True)
_create = VolunteerCreateSchema()
_update = VolunteerUpdateSchema()


@admin_bp.route('/<slug>/volunteers', methods=['GET'])
@require_staff
def list_volunteers(slug):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'

    q = Volunteer.query.filter_by(instance_id=g.instance.id)
    if not include_deleted:
        q = q.filter(Volunteer.deleted_at.is_(None))
    q = q.order_by(Volunteer.name)

    total = q.count()
    items = q.paginate(page=page, per_page=per_page, error_out=False).items
    return paginated(_many.dump(items), total, page, per_page)


@admin_bp.route('/<slug>/volunteers', methods=['POST'])
@require_instance_admin
def create_volunteer(slug):
    try:
        data = _create.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    email = (data.get('email') or '').strip().lower() or None
    if email and Volunteer.query.filter_by(instance_id=g.instance.id, email=email).first():
        return error('E-Mail-Adresse bereits vergeben', 409)

    volunteer = Volunteer(instance_id=g.instance.id, name=data['name'].strip(), email=email)
    if data.get('password'):
        if not validate_password_strength(data['password']):
            return error('Passwort zu schwach', 400)
        volunteer.set_password(data['password'])

    db.session.add(volunteer)
    _log(g.instance.id, f'Helfer angelegt: {volunteer.name}', g.current_user)
    db.session.commit()
    return created(_schema.dump(volunteer))


@admin_bp.route('/<slug>/volunteers/<int:volunteer_id>', methods=['GET'])
@require_staff
def get_volunteer(slug, volunteer_id):
    volunteer = _get_or_404(volunteer_id, g.instance.id)
    return ok(_schema.dump(volunteer))


@admin_bp.route('/<slug>/volunteers/<int:volunteer_id>', methods=['PUT'])
@require_instance_admin
def update_volunteer(slug, volunteer_id):
    volunteer = _get_or_404(volunteer_id, g.instance.id)
    try:
        data = _update.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    if 'email' in data:
        email = (data['email'] or '').strip().lower() or None
        existing = Volunteer.query.filter_by(instance_id=g.instance.id, email=email).first()
        if existing and existing.id != volunteer_id:
            return error('E-Mail-Adresse bereits vergeben', 409)
        volunteer.email = email
    if 'name' in data:
        volunteer.name = data['name'].strip()
    if data.get('password'):
        if not validate_password_strength(data['password']):
            return error('Passwort zu schwach', 400)
        volunteer.set_password(data['password'])

    _log(g.instance.id, f'Helfer geändert: {volunteer.name}', g.current_user)
    db.session.commit()
    return ok(_schema.dump(volunteer))


@admin_bp.route('/<slug>/volunteers/<int:volunteer_id>', methods=['DELETE'])
@require_instance_admin
def delete_volunteer(slug, volunteer_id):
    volunteer = _get_or_404(volunteer_id, g.instance.id)
    volunteer.soft_delete()
    _log(g.instance.id, f'Helfer pseudonymisiert (ID={volunteer_id})', g.current_user)
    db.session.commit()
    return no_content()


@admin_bp.route('/<slug>/volunteers/<int:volunteer_id>/permanent', methods=['DELETE'])
@require_admin
def permanent_delete_volunteer(slug, volunteer_id):
    """Endgültiges Löschen – nur Global-Admins. Für DSGVO-Löschanfragen."""
    from flask import g as _g
    # Instanz manuell auflösen (kein @require_instance_admin hier)
    from ...models import Instance
    instance = Instance.query.filter_by(slug=slug).first_or_404()
    volunteer = _get_or_404(volunteer_id, instance.id)
    _log(instance.id, f'Helfer endgültig gelöscht (ID={volunteer_id})', _g.current_user)
    db.session.delete(volunteer)
    db.session.commit()
    return no_content()


@admin_bp.route('/<slug>/volunteers/<int:volunteer_id>/reset-password', methods=['POST'])
@require_instance_admin
def reset_volunteer_password(slug, volunteer_id):
    volunteer = _get_or_404(volunteer_id, g.instance.id)
    password = (request.get_json() or {}).get('password', '')
    if not validate_password_strength(password):
        return error('Passwort zu schwach (mind. 8 Zeichen, 1 Ziffer, 1 Sonderzeichen)', 400)
    volunteer.set_password(password)
    db.session.commit()
    return ok(message='Passwort wurde geändert')


def _get_or_404(volunteer_id, instance_id):
    from flask import abort
    volunteer = Volunteer.query.filter_by(id=volunteer_id, instance_id=instance_id).first()
    if not volunteer:
        abort(404)
    return volunteer


def _log(instance_id, details, actor):
    db.session.add(ActivityLog(
        instance_id=instance_id,
        event_type=ActivityLog.AUDIT_DATA,
        volunteer_name=getattr(actor, 'email', str(actor)),
        actor_type=getattr(actor, 'role', 'admin'),
        details=details,
    ))
