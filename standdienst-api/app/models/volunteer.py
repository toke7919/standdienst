import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

from ..extensions import db


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class Volunteer(db.Model):
    __tablename__ = 'volunteers'

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(
        db.Integer, db.ForeignKey('instances.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    reset_token = db.Column(db.String(64), nullable=True, index=True)
    reset_token_expires = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))
    consent_given_at = db.Column(db.DateTime(timezone=True), nullable=True)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    registrations = db.relationship(
        'Registration', backref='volunteer', lazy='dynamic', cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.UniqueConstraint('instance_id', 'email', name='uq_volunteer_email_instance'),
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def has_login(self) -> bool:
        return self.email is not None and self.password_hash is not None and not self.is_deleted

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(
            password.encode(), bcrypt.gensalt(rounds=12)
        ).decode()

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
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
        return 'volunteer'

    def get_jwt_identity(self):
        return f'volunteer_{self.id}'

    def __repr__(self):
        return f'<Volunteer {self.name}>'
