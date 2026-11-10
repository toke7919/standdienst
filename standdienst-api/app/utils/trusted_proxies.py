"""Echte Client-IP hinter vertrauenswürdigen Reverse-Proxys.

Betriebskette: Client → externer Proxy (z. B. NPMPlus) → Frontend-/Host-nginx → API.
ProxyFix(x_for=1) vertraut genau dem nginx davor und setzt REMOTE_ADDR auf den
letzten X-Forwarded-For-Eintrag – bei externem Proxy ist das dessen IP. Steht
diese IP in ``GlobalSettings.trusted_proxies``, geht ``TrustedProxyMiddleware``
in X-Forwarded-For weiter nach links bis zur ersten nicht vertrauenswürdigen IP.

Konfigurationsfehler werden beim Speichern abgewiesen (``parse_networks``).
"""
import ipaddress
import logging
import re
import time

log = logging.getLogger(__name__)

_TTL = 30  # Sekunden; pro Worker, max. 30 s Drift bei Multi-Worker-Betrieb
_RETRY_AFTER_ERROR = 10
_cache: dict = {'networks': [], 'expires': 0.0}


def parse_networks(raw: str | None) -> list:
    """Komma-/zeilengetrennte IP/CIDR-Liste → ip_network-Liste.

    Wirft ValueError bei ungültigen Einträgen und bei Netzen mit Präfix /0
    (sonst könnte jeder Client seine IP per X-Forwarded-For fälschen).
    """
    networks = []
    for entry in re.split(r'[,\s]+', raw or ''):
        if not entry:
            continue
        try:
            net = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            raise ValueError(f'Ungültiger Eintrag: {entry} (erwartet IP-Adresse oder CIDR)') from None
        if net.prefixlen == 0:
            raise ValueError(f'Netz zu weit: {entry} – damit könnte jeder Client seine IP fälschen')
        networks.append(net)
    return networks


def normalize(raw: str | None) -> str | None:
    """Kanonische Speicherform: 'a, b, c' oder None wenn leer."""
    entries = [e for e in re.split(r'[,\s]+', raw or '') if e]
    return ', '.join(entries) or None


def _is_trusted(ip: str, networks) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def resolve_client_ip(remote_addr: str, forwarded_for: str | None, networks) -> str:
    """Geht X-Forwarded-For von rechts durch, solange der jeweilige Absender
    vertrauenswürdig ist, und liefert die erste nicht vertrauenswürdige IP."""
    if not networks or not remote_addr or not _is_trusted(remote_addr, networks):
        return remote_addr
    hops = [h.strip() for h in (forwarded_for or '').split(',') if h.strip()]
    # Der letzte Eintrag ist remote_addr selbst (von ProxyFix übernommen).
    if hops and hops[-1] == remote_addr:
        hops.pop()
    client = remote_addr
    while hops:
        candidate = hops.pop()
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            log.warning('Ungültiger X-Forwarded-For-Eintrag von %s: %r', client, candidate)
            break
        client = candidate
        if not _is_trusted(client, networks):
            break
    return client


def invalidate() -> None:
    _cache['expires'] = 0.0


def _networks(app) -> list:
    if time.monotonic() < _cache['expires']:
        return _cache['networks']
    try:
        from sqlalchemy import select
        from ..extensions import db
        from ..models import GlobalSettings
        with app.app_context():
            gs = db.session.scalars(select(GlobalSettings)).first()
            raw = gs.trusted_proxies if gs else None
        _cache['networks'] = parse_networks(raw)
        _cache['expires'] = time.monotonic() + _TTL
    except Exception:
        # Ohne lesbare Einstellung keine Proxy-Auswertung (sichere Seite) –
        # Fehler protokollieren, Request nicht scheitern lassen, bald erneut versuchen.
        log.exception('Vertrauenswürdige Proxys konnten nicht geladen werden')
        _cache['networks'] = []
        _cache['expires'] = time.monotonic() + _RETRY_AFTER_ERROR
    return _cache['networks']


class TrustedProxyMiddleware:
    """WSGI-Middleware innerhalb von ProxyFix: ersetzt REMOTE_ADDR durch die
    echte Client-IP, wenn die Anfrage über einen vertrauenswürdigen Proxy kam."""

    def __init__(self, wsgi_app, flask_app):
        self.wsgi_app = wsgi_app
        self.flask_app = flask_app

    def __call__(self, environ, start_response):
        remote = environ.get('REMOTE_ADDR')
        networks = _networks(self.flask_app)
        if networks:
            environ['REMOTE_ADDR'] = resolve_client_ip(
                remote, environ.get('HTTP_X_FORWARDED_FOR'), networks)
        return self.wsgi_app(environ, start_response)
