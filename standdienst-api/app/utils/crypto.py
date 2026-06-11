"""Transparente Fernet-Verschlüsselung für sensitive DB-Spalten."""
import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

log = logging.getLogger(__name__)


class EncryptedStr(TypeDecorator):
    """SQLAlchemy-TypeDecorator für symmetrisch verschlüsselte Strings.

    Nutzt den SECRET_KEY der Installation. Bestehende Klartextwerte werden
    beim Lesen transparent zurückgegeben; beim nächsten Schreiben werden sie
    automatisch verschlüsselt.
    """
    impl = String
    cache_ok = True

    def _fernet(self) -> Fernet:
        key = base64.urlsafe_b64encode(
            hashlib.sha256(current_app.config['SECRET_KEY'].encode()).digest()
        )
        return Fernet(key)

    def process_bind_param(self, value, dialect):
        if not value:
            return value
        return self._fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if not value:
            return value
        try:
            return self._fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Entweder ein Klartextwert aus der Zeit vor der Verschlüsselung
            # oder ein mit anderem SECRET_KEY verschlüsselter Wert. Letzteres ist
            # ein Konfigurationsfehler (z.B. Key rotiert) – darum protokollieren,
            # damit es nicht stillschweigend als "Klartext" durchrutscht.
            log.warning('EncryptedStr: Entschlüsselung fehlgeschlagen – Wert wird '
                        'als Klartext behandelt (möglicher SECRET_KEY-Wechsel?)')
            return value
