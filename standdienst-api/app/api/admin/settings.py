import os
from flask import request, g, current_app
from marshmallow import ValidationError
from werkzeug.utils import secure_filename

from . import admin_bp
from ...extensions import db
from ...models import SiteSettings, GlobalSettings, MailSettings, ActivityLog
from ...schemas.instance import (
    GlobalSettingsSchema, GlobalSettingsUpdateSchema,
    MailSettingsSchema, MailSettingsUpdateSchema,
)
from ...schemas.settings import SiteSettingsSchema, SiteSettingsUpdateSchema
from ...utils.auth import require_admin, require_instance_admin
from ...utils.sanitizer import sanitize_html
from ...utils.responses import ok, error, optimistic_lock_conflict
from ...utils.mail import send_mail, is_mail_configured, apply_db_mail_config
from ...utils.settings_cache import invalidate_site, invalidate_global

_site_schema = SiteSettingsSchema()
_site_update = SiteSettingsUpdateSchema()
_global_schema = GlobalSettingsSchema()
_global_update = GlobalSettingsUpdateSchema()
_mail_schema = MailSettingsSchema()
_mail_update = MailSettingsUpdateSchema()

_ALLOWED_LOGO = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


@admin_bp.route('/<slug>/settings', methods=['GET'])
@require_instance_admin
def get_site_settings(slug):
    settings = SiteSettings.query.filter_by(instance_id=g.instance.id).first_or_404()
    return ok(_site_schema.dump(settings))


@admin_bp.route('/<slug>/settings', methods=['PUT'])
@require_instance_admin
def update_site_settings(slug):
    raw = request.get_json() or {}
    try:
        data = _site_update.load(raw)
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    settings = SiteSettings.query.filter_by(instance_id=g.instance.id).first_or_404()

    if optimistic_lock_conflict(settings, raw.get('updated_at')):
        return error('Datensatz wurde zwischenzeitlich geändert', 409)

    for key in ('instance_impressum_html', 'privacy_policy_html', 'lock_message'):
        if key in data and data[key]:
            data[key] = sanitize_html(data[key])

    for key, value in data.items():
        setattr(settings, key, value)

    _log(g.instance.id, 'Instanz-Einstellungen geändert', g.current_user)
    db.session.commit()
    invalidate_site(g.instance.id)
    return ok(_site_schema.dump(settings))


@admin_bp.route('/<slug>/settings/logo', methods=['POST'])
@require_instance_admin
def upload_logo(slug):
    if 'logo' not in request.files:
        return error('Keine Datei übergeben', 400)

    file = request.files['logo']
    ext = (file.filename or '').rsplit('.', 1)[-1].lower()
    if ext not in _ALLOWED_LOGO:
        return error(f'Ungültiges Dateiformat (erlaubt: {", ".join(sorted(_ALLOWED_LOGO))})', 400)

    raw = file.read()
    try:
        from PIL import Image
        import io as _io
        img = Image.open(_io.BytesIO(raw))
        img.verify()
        img = Image.open(_io.BytesIO(raw))  # erneut öffnen nach verify()
        png_buf = _io.BytesIO()
        img.convert('RGBA').save(png_buf, format='PNG', optimize=True)
        png_bytes = png_buf.getvalue()
    except Exception:
        return error('Ungültige Bilddatei', 400)

    filename = f'logo_{g.instance.slug}.png'
    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    # Alte Datei mit ggf. anderem Format entfernen
    settings = SiteSettings.query.filter_by(instance_id=g.instance.id).first_or_404()
    old = settings.logo_filename
    if old and old != filename:
        old_path = os.path.join(upload_dir, old)
        try:
            os.unlink(old_path)
        except OSError:
            pass

    with open(os.path.join(upload_dir, filename), 'wb') as fh:
        fh.write(png_bytes)

    settings.logo_filename = filename
    db.session.commit()
    return ok({'logo_filename': filename})


@admin_bp.route('/settings/global', methods=['GET'])
@require_admin
def get_global_settings():
    settings = GlobalSettings.query.first()
    if not settings:
        settings = GlobalSettings()
        db.session.add(settings)
        db.session.commit()
    return ok(_global_schema.dump(settings))


@admin_bp.route('/settings/global', methods=['PUT'])
@require_admin
def update_global_settings():
    raw = request.get_json() or {}
    try:
        data = _global_update.load(raw)
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    settings = GlobalSettings.query.first()
    if not settings:
        settings = GlobalSettings()
        db.session.add(settings)

    if optimistic_lock_conflict(settings, raw.get('updated_at')):
        return error('Datensatz wurde zwischenzeitlich geändert', 409)

    for key in ('provider_impressum_html', 'impressum_template_html', 'datenschutz_template_html'):
        if key in data and data[key]:
            data[key] = sanitize_html(data[key])

    for key, value in data.items():
        setattr(settings, key, value)

    _log(None, 'Globale Einstellungen geändert', g.current_user)
    db.session.commit()
    invalidate_global()
    return ok(_global_schema.dump(settings))


@admin_bp.route('/settings/mail', methods=['GET'])
@require_admin
def get_mail_settings():
    settings = MailSettings.query.first()
    if not settings:
        settings = MailSettings()
        db.session.add(settings)
        db.session.commit()
    if settings.mail_server:
        apply_db_mail_config(settings)
    return ok(_mail_schema.dump(settings))


@admin_bp.route('/settings/mail', methods=['PUT'])
@require_admin
def update_mail_settings():
    raw = request.get_json() or {}
    try:
        data = _mail_update.load(raw)
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    settings = MailSettings.query.first()
    if not settings:
        settings = MailSettings()
        db.session.add(settings)

    if optimistic_lock_conflict(settings, raw.get('updated_at')):
        return error('Datensatz wurde zwischenzeitlich geändert', 409)

    for key, value in data.items():
        setattr(settings, key, value)

    _log(None, 'Mail-Einstellungen geändert', g.current_user)
    db.session.commit()
    if settings.mail_server:
        apply_db_mail_config(settings)
    return ok(_mail_schema.dump(settings))


@admin_bp.route('/settings/mail/test', methods=['POST'])
@require_admin
def send_test_mail():
    if not is_mail_configured(current_app):
        return error('E-Mail nicht konfiguriert', 503)
    to = getattr(g.current_user, 'email', None)
    if not to:
        return error('Kein E-Mail-Konto für diesen Admin hinterlegt', 400)
    try:
        send_mail(
            to=to,
            subject='Standdienst – Testmail',
            html='<p>Diese Testmail wurde erfolgreich über die konfigurierte SMTP-Verbindung gesendet.</p>',
        )
        return ok(message=f'Testmail an {to} gesendet')
    except Exception:
        current_app.logger.exception('Testmail-Versand fehlgeschlagen')
        return error('E-Mail-Versand fehlgeschlagen', 500)


def _log(instance_id, details, actor):
    db.session.add(ActivityLog(
        instance_id=instance_id,
        event_type=ActivityLog.AUDIT_SETTINGS,
        volunteer_name=getattr(actor, 'email', str(actor)),
        actor_type=getattr(actor, 'role', 'admin'),
        ip_address=request.remote_addr,
        details=details,
    ))
