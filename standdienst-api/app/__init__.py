import logging
import os
from uuid import uuid4

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import select, func

from .config import Config
from .extensions import db, migrate, jwt, mail, limiter, cors
from .utils.logging_setup import init_logging

log = logging.getLogger(__name__)


def create_app(config_class=Config):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    _validate_production_config(app)
    init_logging(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_request_hooks(app)
    _register_spa_fallback(app)
    _init_db(app)

    return app


def _validate_production_config(app):
    """Erzwingt sichere Produktiv-Einstellungen.

    Im Produktivbetrieb (PostgreSQL-DB) muss das Rate-Limit über Redis laufen.
    Mit dem Default 'memory://' gelten Limits nur pro Gunicorn-Worker (real
    Limit × Worker) und gehen bei jedem Neustart verloren – das schwächt den
    Brute-Force-Schutz erheblich. SQLite-Dev und Tests bleiben ausgenommen.
    """
    if app.config.get('TESTING'):
        return
    is_production = str(app.config.get('SQLALCHEMY_DATABASE_URI', '')).startswith('postgresql')
    if not is_production:
        return
    storage = str(app.config.get('RATELIMIT_STORAGE_URI', 'memory://'))
    if not (storage.startswith('redis://') or storage.startswith('rediss://')):
        raise RuntimeError(
            'RATELIMIT_STORAGE_URI muss in Produktion auf Redis zeigen '
            '(z.B. redis://127.0.0.1:6379/0). Der Default "memory://" ist mit '
            'mehreren Gunicorn-Workern unsicher und nicht persistent.'
        )


def _init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        origins=[app.config['FRONTEND_URL']],
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization', 'X-CSRF-TOKEN'],
    )


def _register_blueprints(app):
    from .api.auth import auth_bp
    from .api.passkey import passkey_bp
    from .api.public import public_bp
    from .api.volunteer import volunteer_bp
    from .api.admin import admin_bp
    from .api.setup import setup_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(passkey_bp, url_prefix='/api/auth/passkey')
    app.register_blueprint(public_bp, url_prefix='/api/public')
    app.register_blueprint(volunteer_bp, url_prefix='/api/volunteer')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(setup_bp, url_prefix='/api/setup')

    # Swagger UI (OpenAPI-Dokumentation)
    from flask_swagger_ui import get_swaggerui_blueprint
    import os
    spec_url = '/static/openapi.yaml'
    swaggerui_bp = get_swaggerui_blueprint(
        '/api/docs',
        spec_url,
        config={'app_name': 'Standdienst API'},
    )
    app.register_blueprint(swaggerui_bp, url_prefix='/api/docs')

    @app.route('/static/openapi.yaml')
    def serve_openapi_spec():
        static_dir = os.path.join(app.root_path, '..', 'static')
        return send_from_directory(os.path.abspath(static_dir), 'openapi.yaml')


def _register_request_hooks(app):
    from .extensions import limiter
    from .utils.ip_whitelist import is_whitelisted

    @limiter.request_filter
    def _bypass_whitelisted():
        return is_whitelisted(request.remote_addr)

    @app.before_request
    def _inject_request_id():
        g.request_id = uuid4().hex[:8]
        log.debug('%s %s', request.method, request.path)

    @app.after_request
    def _log_response(response):
        if response.status_code >= 400:
            log.warning('%s %s → %d', request.method, request.path, response.status_code)
        else:
            log.debug('%s %s → %d', request.method, request.path, response.status_code)
        return response

    @app.after_request
    def _security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        ct = response.content_type or ''
        if 'text/html' in ct:
            # CSP für das SPA-Dokument. 'unsafe-inline' bei style-src ist für Vue
            # :style-Bindings nötig; Google Fonts werden explizit erlaubt.
            response.headers['Content-Security-Policy'] = (
                "default-src 'none'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: blob:; "
                "connect-src 'self'; "
                "manifest-src 'self'; "
                "worker-src 'self'; "
                "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
            )
        elif 'json' in ct or 'text/plain' in ct:
            response.headers['Content-Security-Policy'] = "default-src 'none'"
        return response


def _register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error=str(e.description)), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify(error='Nicht autorisiert'), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify(error='Zugriff verweigert'), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error='Nicht gefunden'), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify(error='Zu viele Anfragen – bitte warten'), 429

    @app.errorhandler(500)
    def server_error(e):
        log.exception('Unbehandelter Serverfehler: %s %s', request.method, request.path)
        return jsonify(error='Interner Serverfehler'), 500

    @jwt.expired_token_loader
    def expired_token(_jwt_header, _jwt_data):
        return jsonify(error='Token abgelaufen', code='token_expired'), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify(error='Ungültiges Token', reason=reason), 401

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify(error='Authentifizierung erforderlich', reason=reason), 401


def _register_spa_fallback(app):
    dist_path = os.path.join(app.root_path, '..', 'static', 'dist')
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(os.path.abspath(upload_folder), filename)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def spa_fallback(path):
        if path.startswith('api/'):
            return jsonify(error='Nicht gefunden'), 404
        full = os.path.join(dist_path, path)
        if path and os.path.isfile(full):
            return send_from_directory(dist_path, path)
        index = os.path.join(dist_path, 'index.html')
        if os.path.isfile(index):
            return send_from_directory(dist_path, 'index.html')
        return jsonify(error='Frontend noch nicht gebaut'), 503


def _init_db(app):
    if app.config.get('TESTING'):
        with app.app_context():
            db.create_all()
            _seed_admin(app)
        return
    # Produktiv: DB-Mail-Einstellungen in Flask-Config laden (falls kein env-SMTP gesetzt)
    if not app.config.get('MAIL_SERVER'):
        with app.app_context():
            try:
                from .models import MailSettings
                from .utils.mail import apply_db_mail_config
                ms = db.session.scalars(select(MailSettings)).first()
                if ms and ms.mail_server:
                    apply_db_mail_config(ms)
            except Exception:
                pass


def _seed_admin(app):
    from .models import Admin, GlobalSettings
    if db.session.scalar(select(func.count()).select_from(Admin)) > 0:
        return
    admin_email = app.config.get('ADMIN_EMAIL', 'admin@example.com')
    admin_pw = os.getenv('ADMIN_PASSWORD')
    if not admin_pw:
        return
    admin = Admin(email=admin_email, is_primary=True)
    admin.set_password(admin_pw)
    db.session.add(admin)
    # Setup in Tests als abgeschlossen markieren
    gs = db.session.scalars(select(GlobalSettings)).first() or GlobalSettings()
    gs.setup_complete = True
    db.session.add(gs)
    db.session.commit()
