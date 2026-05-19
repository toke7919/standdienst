import time
from sqlalchemy.orm import make_transient

_cache: dict = {}
_TTL = 30  # Sekunden; pro Worker, max. 30s Drift bei Multi-Worker-Betrieb


def _get(key: str):
    entry = _cache.get(key)
    if entry:
        value, expires = entry
        if time.monotonic() < expires:
            return value, True
    return None, False


def _detach(obj):
    """ORM-Objekt vom Session-Kontext lösen, damit es sicher gecacht werden kann."""
    if obj is not None:
        make_transient(obj)
    return obj


def get_site_settings(instance_id: int):
    key = f's:{instance_id}'
    value, hit = _get(key)
    if hit:
        return value
    from ..models import SiteSettings
    value = SiteSettings.query.filter_by(instance_id=instance_id).first()
    _detach(value)
    _cache[key] = (value, time.monotonic() + _TTL)
    return value


def get_global_settings():
    value, hit = _get('g')
    if hit:
        return value
    from ..models import GlobalSettings
    value = GlobalSettings.query.first()
    _detach(value)
    _cache['g'] = (value, time.monotonic() + _TTL)
    return value


def invalidate_site(instance_id: int) -> None:
    _cache.pop(f's:{instance_id}', None)


def invalidate_global() -> None:
    _cache.pop('g', None)
