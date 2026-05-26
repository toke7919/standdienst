import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

from ..extensions import db
from .instance import organizer_instances


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class Organizer(db.Model):
    """Eingeschränkte Admin-Rolle; immer einer oder mehreren Instanzen zugeordnet.

    is_instance_admin=True  → volle Kontrolle über zugeordnete Instanzen
    is_instance_admin=False → operativer Zugriff (Dienste, Termine, Eintragungen)
    """
    __tablename__ = 'organizers'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    reset_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    reset_token_expires = db.Column(db.DateTime(timezone=True), nullable=True)
    jwt_version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_enabled = db.Column(db.Boolean, nullable=False, default=False)
    totp_backup_codes = db.Column(db.JSON, nullable=True)
    is_instance_admin = db.Column(db.Boolean, nullable=False, default=False)
    notifications_enabled = db.Column(db.Boolean, nullable=False, default=True)

    instances = db.relationship(
        'Instance',
        secondary=organizer_instances,
        backref=db.backref('organizers', lazy='dynamic'),
        lazy='dynamic',
    )

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
    def has_login(self) -> bool:
        return self.password_hash is not None

    @property
    def role(self):
        return 'organizer'

    def rotate_jwt(self):
        self.jwt_version = (self.jwt_version or 1) + 1

    def get_jwt_identity(self):
        return f'organizer_{self.id}'

    def has_instance_access(self, instance_id: int) -> bool:
        return self.instances.filter_by(id=instance_id).first() is not None

    def is_admin_for(self, instance_id: int) -> bool:
        row = db.session.execute(
            organizer_instances.select().where(
                organizer_instances.c.organizer_id == self.id,
                organizer_instances.c.instance_id == instance_id,
            )
        ).first()
        return bool(row and row.is_instance_admin)

    def is_primary_for(self, instance_id: int) -> bool:
        row = db.session.execute(
            organizer_instances.select().where(
                organizer_instances.c.organizer_id == self.id,
                organizer_instances.c.instance_id == instance_id,
            )
        ).first()
        return bool(row and row.is_primary)

    def __repr__(self):
        return f'<Organizer {self.name}>'
