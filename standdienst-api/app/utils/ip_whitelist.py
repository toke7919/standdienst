import ipaddress
import time

_cache: dict = {'networks': [], 'expires': 0.0}
_TTL = 60  # Sekunden


def is_whitelisted(ip: str) -> bool:
    if not ip:
        return False
    if time.time() > _cache['expires']:
        _refresh()
    if not _cache['networks']:
        return False
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in _cache['networks'])
    except ValueError:
        return False


def invalidate():
    _cache['expires'] = 0.0


def _refresh() -> None:
    try:
        from sqlalchemy import select
        from ..extensions import db
        from ..models import GlobalSettings
        gs = db.session.scalars(select(GlobalSettings)).first()
        raw = gs.ip_whitelist if gs else None
        networks = []
        if raw:
            for entry in raw.split(','):
                entry = entry.strip()
                if entry:
                    try:
                        networks.append(ipaddress.ip_network(entry, strict=False))
                    except ValueError:
                        pass
        _cache['networks'] = networks
        _cache['expires'] = time.time() + _TTL
    except Exception:
        _cache['expires'] = time.time() + 10
