from flask import request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()
cors = CORS()


def _real_ip() -> str:
    """Liest die echte Client-IP hinter Nginx.

    Nginx setzt X-Real-IP auf $remote_addr (direkte Client-IP) – zuverlässiger
    als X-Forwarded-For, da ProxyFix(x_for=1) bei nur einem Eintrag auf
    127.0.0.1 zurückfällt und alle Nutzer denselben Zähler teilen würden.
    """
    return (
        request.environ.get('HTTP_X_REAL_IP')
        or request.remote_addr
        or 'unknown'
    )


limiter = Limiter(key_func=_real_ip)
