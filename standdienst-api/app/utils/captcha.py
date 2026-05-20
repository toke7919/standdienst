"""Altcha Proof-of-Work CAPTCHA (RFC-kompatibel, keine externen Abhängigkeiten)."""
import base64
import hashlib
import hmac as _hmac
import json
import secrets
import time
from flask import current_app

_EXPIRES = 600  # 10 Minuten Gültigkeit


def _key() -> bytes:
    return hashlib.sha256(current_app.config['SECRET_KEY'].encode()).digest()


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
        if '?expires=' in salt:
            exp_str = salt.split('?expires=')[1].split('&')[0]
            if time.time() > int(exp_str):
                return False

        # Proof-of-Work prüfen
        computed = hashlib.sha256(f'{salt}{number}'.encode()).hexdigest()
        return _hmac.compare_digest(computed, challenge)
    except Exception:
        return False
