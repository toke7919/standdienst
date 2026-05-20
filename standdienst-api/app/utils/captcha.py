import secrets
import time
from flask import session

_TTL = 300  # Sekunden


def generate_captcha() -> dict:
    a = secrets.randbelow(90) + 10   # 10–99
    b = secrets.randbelow(90) + 10   # 10–99
    session['captcha'] = {'answer': a + b, 'expires': time.time() + _TTL}
    return {'question': f'{a} + {b} = ?'}


def verify_captcha(answer: int) -> bool:
    data = session.pop('captcha', None)
    if not data:
        return False
    if time.time() > data['expires']:
        return False
    return int(answer) == data['answer']
