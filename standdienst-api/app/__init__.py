import os
from flask import Flask, jsonify, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .extensions import db, migrate, jwt, mail, limiter, cors


def create_app(config_class=Config):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_spa_fallback(app)
    _init_db(app)
    _start_scheduler(app)

    return app


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
    from .api.public import public_bp
    from .api.volunteer import volunteer_bp
    from .api.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(public_bp, url_prefix='/api/public')
    app.register_blueprint(volunteer_bp, url_prefix='/api/volunteer')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')


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


def _start_scheduler(app):
    from .utils.scheduler import init_scheduler
    init_scheduler(app)


def _init_db(app):
    if app.config.get('TESTING'):
        with app.app_context():
            db.create_all()
            _seed_admin(app)


def _seed_admin(app):
    from .models import Admin
    if Admin.query.count() > 0:
        return
    admin_email = app.config.get('ADMIN_EMAIL', 'admin@example.com')
    admin_pw = os.getenv('ADMIN_PASSWORD')
    if not admin_pw:
        return
    admin = Admin(email=admin_email, is_primary=True)
    admin.set_password(admin_pw)
    db.session.add(admin)
    db.session.commit()
