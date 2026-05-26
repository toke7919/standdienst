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
from ...utils.mail import send_mail, is_mail_configured, apply_db_mail_config, get_platform_logo_for_email
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
    db.session.refresh(settings)
    return ok({'logo_filename': filename, 'updated_at': settings.updated_at.isoformat() if settings.updated_at else None})


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


def _reload_mail_config():
    """Lädt aktuelle DB-Mail-Einstellungen in den Flask-Config des laufenden Workers."""
    ms = MailSettings.query.first()
    if not (ms and ms.mail_server):
        return
    from ...extensions import mail as _mail
    current_app.config.update(
        MAIL_SERVER=ms.mail_server,
        MAIL_PORT=ms.mail_port or 587,
        MAIL_USE_TLS=ms.mail_use_tls,
        MAIL_USERNAME=ms.mail_username or '',
        MAIL_PASSWORD=ms.mail_password or '',
        MAIL_DEFAULT_SENDER=ms.mail_default_sender or '',
        MAIL_SENDER_NAME=ms.mail_sender_name or '',
    )
    current_app.extensions['mail'] = _mail.init_mail(
        current_app.config, current_app.debug, current_app.testing
    )


@admin_bp.route('/settings/mail/test', methods=['POST'])
@require_admin
def send_test_mail():
    _reload_mail_config()
    if not is_mail_configured(current_app):
        return error('E-Mail nicht konfiguriert', 503)
    body = request.get_json() or {}
    to = (body.get('to') or '').strip() or getattr(g.current_user, 'email', None)
    if not to:
        return error('Keine Empfängeradresse angegeben', 400)
    try:
        send_mail(
            to=to,
            subject='Standdienst – Testmail',
            html='<p>Diese Testmail wurde erfolgreich über die konfigurierte SMTP-Verbindung gesendet.</p>',
        )
        return ok(message=f'Testmail an {to} gesendet')
    except Exception as exc:
        current_app.logger.exception('Testmail-Versand fehlgeschlagen')
        return error(f'SMTP-Fehler: {exc}', 500)


@admin_bp.route('/settings/mail/test-type', methods=['POST'])
@require_admin
def send_typed_test_mail():
    _reload_mail_config()
    if not is_mail_configured(current_app):
        return error('E-Mail nicht konfiguriert', 503)
    body = request.get_json() or {}
    mail_type = (body.get('type') or '').strip()
    to = (body.get('to') or '').strip()
    slug = (body.get('instance_slug') or '').strip() or None
    if not mail_type:
        return error('Kein Mail-Typ angegeben', 400)
    if not to:
        return error('Keine Empfängeradresse angegeben', 400)

    from ...utils.mail import (
        get_logo_for_email,
        build_welcome_email, build_reset_email, build_organizer_invite_email,
        build_shift_confirmation_email, build_reminder_email, build_organizer_digest_email,
        build_daten_auskunft_email,
    )
    from ...utils.settings_cache import get_site_settings, get_global_settings
    from ..public import _base_url
    base_url = _base_url()

    # Branding aus Instanz- oder Global-Settings laden
    gs = get_global_settings()
    copyright_text = gs.copyright_text if gs else None
    primary_color = None
    logo_url = None
    inst_name = 'Muster-Instanz'

    if slug:
        from ...models import Instance
        inst = Instance.query.filter_by(slug=slug).first()
        if inst:
            inst_name = inst.name
            settings = get_site_settings(inst.id)
            if settings:
                primary_color = settings.primary_color or primary_color
                inst_name = settings.site_title or inst_name
                logo_url = get_logo_for_email(settings.logo_filename, base_url)

    # Fallback auf Plattform-Logo wenn keine Instanz oder kein Instanz-Logo
    if not logo_url:
        logo_url = get_platform_logo_for_email()

    eff_slug = slug or 'beispiel'
    DUMMY = {
        'name': 'Max Mustermann',
        'email': to,
        'stand': 'Stand 1',
        'date': '28.06.2025',
        'time': '10:00–14:00',
        'setup_url': f'{base_url}/admin/reset-password?token=BEISPIELTOKEN',
        'reset_url': f'{base_url}/admin/reset-password?token=BEISPIELTOKEN',
        'welcome_url': f'{base_url}/{eff_slug}/welcome/BEISPIELTOKEN',
        'inst_name': inst_name,
        'inst_url': f'{base_url}/{eff_slug}',
        'opt_out_vol': f'{base_url}/{eff_slug}/profile',
        'opt_out_org': f'{base_url}/admin/profile',
    }

    def _kw(**extra):
        k = dict(logo_url=logo_url, copyright_text=copyright_text)
        if primary_color:
            k['primary_color'] = primary_color
        k.update(extra)
        return k

    BUILDERS = {
        'welcome': lambda: (
            f'Willkommen – {inst_name}',
            build_welcome_email(DUMMY['name'], inst_name, DUMMY['welcome_url'], base_url,
                                **_kw(slug=slug)),
        ),
        'organizer_invite': lambda: (
            'Dein Organisator-Konto bei Standdienst',
            build_organizer_invite_email(
                DUMMY['name'], DUMMY['setup_url'],
                [{'name': inst_name, 'volunteer_url': DUMMY['inst_url']}],
                base_url,
                **_kw(
                    impressum_url=f'{base_url}/impressum',
                    datenschutz_url=f'{base_url}/datenschutz',
                ),
            ),
        ),
        'reset': lambda: (
            'Passwort zurücksetzen – Standdienst',
            build_reset_email(DUMMY['name'], DUMMY['reset_url'], base_url,
                              **_kw(
                                  slug=slug,
                                  impressum_url=f'{base_url}/impressum' if not slug else None,
                                  datenschutz_url=f'{base_url}/datenschutz' if not slug else None,
                              )),
        ),
        'shift_confirmation': lambda: (
            f'Anmeldebestätigung – {inst_name}',
            build_shift_confirmation_email(
                DUMMY['name'], inst_name, DUMMY['stand'], DUMMY['date'],
                DUMMY['time'], DUMMY['inst_url'], base_url,
                **_kw(slug=slug, opt_out_url=DUMMY['opt_out_vol']),
            ),
        ),
        'reminder': lambda: (
            f'Erinnerung: Schicht morgen – {inst_name}',
            build_reminder_email(
                DUMMY['name'],
                shifts=[{'stand': DUMMY['stand'], 'time': DUMMY['time']}],
                food_items=[],
                instance_title=inst_name,
                base_url=base_url,
                **_kw(slug=slug, opt_out_url=DUMMY['opt_out_vol']),
            ),
        ),
        'digest': lambda: (
            f'Tages-Zusammenfassung – {inst_name}',
            build_organizer_digest_email(
                organizer_name=DUMMY['name'],
                instance_title=inst_name,
                date_label=DUMMY['date'],
                registrations=[{'name': 'Anna Beispiel', 'stand': DUMMY['stand'], 'time': DUMMY['time']}],
                cancellations=[],
                food_donations=[{'name': 'Berta Beispiel', 'food_type': 'Kuchen', 'description': 'Schokoladenkuchen'}],
                base_url=base_url,
                slug=eff_slug,
                **_kw(opt_out_url=DUMMY['opt_out_org']),
            ),
        ),
        'dsgvo_auskunft': lambda: (
            f'Ihre Daten bei {inst_name}',
            build_daten_auskunft_email(
                DUMMY['name'],
                data={
                    'volunteer': {
                        'name': DUMMY['name'],
                        'email': DUMMY['email'],
                        'created_at': '01.01.2025 10:00',
                        'consent_given_at': '01.01.2025 10:00',
                    },
                    'registrations': [{'date': DUMMY['date'], 'stand': DUMMY['stand'],
                                       'start_time': '10:00', 'end_time': '14:00'}],
                    'food_donations': [{'food_type': 'Kuchen', 'description': 'Schokoladenkuchen',
                                        'needs_refrigeration': False}],
                },
                instance_title=inst_name,
                base_url=base_url,
                **_kw(slug=slug),
            ),
        ),
    }

    builder = BUILDERS.get(mail_type)
    if not builder:
        return error(f'Unbekannter Mail-Typ: {mail_type}', 400)

    try:
        subject, html = builder()
        send_mail(to=to, subject=subject, html=html)
        return ok(message=f'Testmail ({mail_type}) an {to} gesendet')
    except Exception as exc:
        current_app.logger.exception('Typisierte Testmail fehlgeschlagen')
        return error(f'SMTP-Fehler: {exc}', 500)


def _log(instance_id, details, actor):
    db.session.add(ActivityLog(
        instance_id=instance_id,
        event_type=ActivityLog.AUDIT_SETTINGS,
        volunteer_name=getattr(actor, 'email', str(actor)),
        actor_type=getattr(actor, 'role', 'admin'),
        ip_address=request.remote_addr,
        details=details,
    ))
