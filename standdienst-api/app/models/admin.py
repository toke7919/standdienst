import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

from ..extensions import db


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class Admin(db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_enabled = db.Column(db.Boolean, nullable=False, default=False)
    reset_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    reset_token_expires = db.Column(db.DateTime(timezone=True), nullable=True)
    jwt_version = db.Column(db.Integer, nullable=False, default=1)

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(
            password.encode(), bcrypt.gensalt(rounds=12)
        ).decode()

    def check_password(self, password: str) -> bool:
        if not self.password_hash or self.password_hash == '!':
            return False
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    def generate_reset_token(self, expiry_seconds: int = 3600) -> str:
        raw = secrets.token_urlsafe(32)
        self.reset_token = _hash_token(raw)
        self.reset_token_expires = datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)
        return raw

    def clear_reset_token(self):
        self.reset_token = None
        self.reset_token_expires = None

    @property
    def is_reset_token_valid(self) -> bool:
        if not self.reset_token or not self.reset_token_expires:
            return False
        expires = self.reset_token_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < expires

    @property
    def role(self):
        return 'admin'

    def rotate_jwt(self):
        self.jwt_version = (self.jwt_version or 1) + 1

    def get_jwt_identity(self):
        return f'admin_{self.id}'

    def __repr__(self):
        return f'<Admin {self.email}>'
