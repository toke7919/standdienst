from datetime import datetime, timezone
from ..extensions import db


class PasskeyCredential(db.Model):
    __tablename__ = 'passkey_credentials'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='CASCADE'), nullable=True, index=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('organizers.id', ondelete='CASCADE'), nullable=True, index=True)
    credential_id = db.Column(db.Text, unique=True, nullable=False)
    public_key = db.Column(db.Text, nullable=False)
    sign_count = db.Column(db.Integer, default=0, nullable=False)
    name = db.Column(db.String(100), nullable=False, default='Passkey')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def owner_identity(self) -> str:
        if self.admin_id:
            return f'admin_{self.admin_id}'
        return f'organizer_{self.organizer_id}'
