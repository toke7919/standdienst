from datetime import datetime, timezone
from ..extensions import db
from ..utils.crypto import EncryptedStr


organizer_instances = db.Table(
    'organizer_instances',
    db.Column('organizer_id', db.Integer,
              db.ForeignKey('organizers.id', ondelete='CASCADE'), primary_key=True),
    db.Column('instance_id', db.Integer,
              db.ForeignKey('instances.id', ondelete='CASCADE'), primary_key=True),
    db.Column('is_primary', db.Boolean, nullable=False, default=False),
    db.Column('is_instance_admin', db.Boolean, nullable=False, default=False),
)


class Instance(db.Model):
    __tablename__ = 'instances'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))
    contact_organisation = db.Column(db.String(200), nullable=True)
    contact_person = db.Column(db.String(200), nullable=True)
    contact_street = db.Column(db.String(200), nullable=True)
    contact_zip_city = db.Column(db.String(100), nullable=True)
    contact_email = db.Column(db.String(200), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    contact_asp = db.Column(db.String(200), nullable=True)
    contact_asp_email = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Instance {self.slug}>'


class GlobalSettings(db.Model):
    __tablename__ = 'global_settings'

    id = db.Column(db.Integer, primary_key=True)
    base_url = db.Column(db.String(500), nullable=True)
    copyright_text = db.Column(db.String(500), nullable=True)
    provider_impressum_html = db.Column(db.Text, nullable=True)
    impressum_template_html = db.Column(db.Text, nullable=True)
    datenschutz_template_html = db.Column(db.Text, nullable=True)
    contact_organisation = db.Column(db.String(200), nullable=True)
    contact_person = db.Column(db.String(200), nullable=True)
    contact_street = db.Column(db.String(200), nullable=True)
    contact_zip_city = db.Column(db.String(100), nullable=True)
    contact_email = db.Column(db.String(200), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    contact_asp = db.Column(db.String(200), nullable=True)
    contact_asp_email = db.Column(db.String(200), nullable=True)
    log_retention_months = db.Column(db.Integer, nullable=False, default=3)
    smb_enabled = db.Column(db.Boolean, nullable=False, default=False)
    smb_server = db.Column(db.String(200), nullable=True)
    smb_share = db.Column(db.String(200), nullable=True)
    smb_path = db.Column(db.String(500), nullable=True)
    smb_username = db.Column(db.String(200), nullable=True)
    smb_password = db.Column(EncryptedStr(500), nullable=True)
    setup_complete = db.Column(db.Boolean, nullable=False, default=False)
    github_pat = db.Column(EncryptedStr(500), nullable=True)
    github_repo = db.Column(db.String(200), nullable=True)
    timezone = db.Column(db.String(100), nullable=False, default='Europe/Berlin')
    volunteer_retention_months = db.Column(db.Integer, nullable=True)
    ip_whitelist = db.Column(db.Text, nullable=True)
    backup_password = db.Column(EncryptedStr(500), nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return '<GlobalSettings>'


class MailSettings(db.Model):
    __tablename__ = 'mail_settings'

    id = db.Column(db.Integer, primary_key=True)
    mail_server = db.Column(db.String(200), nullable=False, default='')
    mail_port = db.Column(db.Integer, nullable=False, default=587)
    mail_use_tls = db.Column(db.Boolean, nullable=False, default=True)
    mail_username = db.Column(db.String(200), nullable=False, default='')
    mail_password = db.Column(EncryptedStr(500), nullable=False, default='')
    mail_default_sender = db.Column(db.String(200), nullable=False, default='')
    mail_sender_name = db.Column(db.String(200), nullable=False, default='')
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f'<MailSettings {self.mail_server}:{self.mail_port}>'
