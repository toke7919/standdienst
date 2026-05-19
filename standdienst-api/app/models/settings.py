from datetime import datetime, timezone
from ..extensions import db


class SiteSettings(db.Model):
    __tablename__ = 'site_settings'

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(
        db.Integer, db.ForeignKey('instances.id', ondelete='CASCADE'),
        nullable=False, unique=True, index=True,
    )
    site_title = db.Column(db.String(200), nullable=False, default='Standdienst')
    primary_color = db.Column(db.String(7), nullable=False, default='#4f46e5')
    logo_filename = db.Column(db.String(200), nullable=True)
    mail_sender_name = db.Column(db.String(200), nullable=False, default='')
    shifts_enabled = db.Column(db.Boolean, nullable=False, default=True)
    food_donations_enabled = db.Column(db.Boolean, nullable=False, default=True)
    food_refrigeration_enabled = db.Column(db.Boolean, nullable=False, default=True)
    site_locked = db.Column(db.Boolean, nullable=False, default=False)
    lock_message = db.Column(db.Text, nullable=True)
    log_retention_months = db.Column(db.Integer, nullable=False, default=3)
    instance_impressum_html = db.Column(db.Text, nullable=True)
    privacy_policy_html = db.Column(db.Text, nullable=True)
    registration_deadline = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def registration_open(self) -> bool:
        if self.registration_deadline is None:
            return True
        deadline = self.registration_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < deadline

    def __repr__(self):
        return f'<SiteSettings instance={self.instance_id}>'
