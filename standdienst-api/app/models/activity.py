from datetime import datetime, timezone
from ..extensions import db


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    SHIFT_REGISTER   = 'shift_register'
    SHIFT_UNREGISTER = 'shift_unregister'
    FOOD_REGISTER    = 'food_register'
    FOOD_UNREGISTER  = 'food_unregister'
    LOGIN_SUCCESS    = 'login_success'
    LOGIN_FAIL       = 'login_fail'
    VOLUNTEER_REGISTER = 'volunteer_register'
    VOLUNTEER_DELETE           = 'volunteer_delete'
    VOLUNTEER_PERMANENT_DELETE = 'volunteer_permanent_delete'
    AUDIT_SETTINGS   = 'audit_settings'
    AUDIT_DATA       = 'audit_data'
    AUDIT_ORGANIZER  = 'audit_organizer'
    AUDIT_ADMIN      = 'audit_admin'

    id = db.Column(db.Integer, primary_key=True)
    # NULL = globale Aktion (Admin-Login, Instanz angelegt, …)
    instance_id = db.Column(
        db.Integer, db.ForeignKey('instances.id', ondelete='SET NULL'),
        nullable=True, index=True,
    )
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True,
    )
    event_type = db.Column(db.String(30), nullable=False, index=True)
    volunteer_name = db.Column(db.String(100), nullable=True)
    volunteer_id = db.Column(db.Integer, nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    details = db.Column(db.Text, nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    actor_type = db.Column(db.String(20), nullable=True)

    def __repr__(self):
        return f'<ActivityLog {self.event_type} {self.timestamp}>'
