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
    """Liefert die echte Client-IP hinter dem vertrauenswürdigen Reverse-Proxy.

    ProxyFix(x_for=1) wertet genau einen Proxy-Hop aus und setzt
    request.remote_addr auf die von Nginx via $proxy_add_x_forwarded_for
    angehängte echte Client-IP. Der direkt vom Client setzbare X-Real-IP-Header
    wird bewusst NICHT mehr gelesen – sonst ließen sich Rate-Limit-, Fail2Ban-
    und Setup-IP-Prüfungen durch Spoofing aushebeln.
    """
    return request.remote_addr or 'unknown'


limiter = Limiter(key_func=_real_ip)
