"""Altcha Proof-of-Work CAPTCHA (RFC-kompatibel, keine externen Abhängigkeiten)."""
import base64
import hashlib
import hmac as _hmac
import json
import secrets
import threading
import time
from flask import current_app

_EXPIRES = 600  # 10 Minuten Gültigkeit

# Replay-Schutz: bereits eingelöste Challenges werden bis zu ihrem Ablauf als
# "verbraucht" markiert. Bevorzugt im gemeinsamen Redis-Store (mehrere Worker),
# sonst prozesslokal als Fallback (Dev/Test, Einzelworker).
_local_consumed: dict[str, float] = {}
_local_lock = threading.Lock()


def _key() -> bytes:
    return hashlib.sha256(current_app.config['SECRET_KEY'].encode()).digest()


def _redis_client():
    uri = current_app.config.get('RATELIMIT_STORAGE_URI', 'memory://')
    if uri.startswith('redis://') or uri.startswith('rediss://'):
        try:
            import redis as _redis
            return _redis.from_url(uri, socket_connect_timeout=2)
        except Exception:
            return None
    return None


def _try_consume(signature: str, ttl: int) -> bool:
    """Markiert eine Challenge atomar als verbraucht.

    Gibt True zurück, wenn sie noch nicht eingelöst war (Erstnutzung), und
    False bei einem Replay-Versuch.
    """
    ttl = max(ttl, 1)
    key = f'altcha:used:{signature}'
    r = _redis_client()
    if r is not None:
        try:
            # SET key 1 NX EX ttl → True nur bei der ersten Einlösung.
            return bool(r.set(key, b'1', nx=True, ex=ttl))
        except Exception:
            pass  # Fallback auf prozesslokalen Speicher
    now = time.time()
    with _local_lock:
        for k in [k for k, exp in _local_consumed.items() if exp < now]:
            _local_consumed.pop(k, None)
        if signature in _local_consumed:
            return False
        _local_consumed[signature] = now + ttl
        return True


def _max_number() -> int:
    return current_app.config.get('ALTCHA_MAX_NUMBER', 100_000)


def generate_challenge() -> dict:
    """Erzeugt eine Altcha-Challenge. Client löst im Schnitt maxnumber/2 Hashes."""
    max_n = _max_number()
    number = secrets.randbelow(max_n)
    expires = int(time.time()) + _EXPIRES
    salt = f'{secrets.token_hex(12)}?expires={expires}'
    algorithm = 'SHA-256'
    challenge = hashlib.sha256(f'{salt}{number}'.encode()).hexdigest()
    sig = _hmac.new(
        _key(),
        f'{algorithm}:{challenge}:{salt}'.encode(),
        hashlib.sha256,
    ).hexdigest()
    return {
        'algorithm': algorithm,
        'challenge': challenge,
        'maxnumber': max_n,
        'salt': salt,
        'signature': sig,
    }


def verify_solution(payload_b64: str) -> bool:
    """Verifiziert eine vom Altcha-Widget gesendete base64-kodierte Lösung."""
    try:
        padded = payload_b64 + '=' * (-len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(padded))
        algorithm = str(payload.get('algorithm', 'SHA-256'))
        challenge = str(payload['challenge'])
        number = int(payload['number'])
        salt = str(payload['salt'])
        signature = str(payload['signature'])

        # HMAC-Signatur prüfen
        expected = _hmac.new(
            _key(),
            f'{algorithm}:{challenge}:{salt}'.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not _hmac.compare_digest(expected, signature):
            return False

        # Ablaufzeit prüfen
        remaining_ttl = _EXPIRES
        if '?expires=' in salt:
            exp_ts = int(salt.split('?expires=')[1].split('&')[0])
            if time.time() > exp_ts:
                return False
            remaining_ttl = int(exp_ts - time.time())

        # Proof-of-Work prüfen
        computed = hashlib.sha256(f'{salt}{number}'.encode()).hexdigest()
        if not _hmac.compare_digest(computed, challenge):
            return False

        # Replay-Schutz: gültige Lösung genau einmal zulassen.
        return _try_consume(signature, remaining_ttl)
    except Exception:
        return False
