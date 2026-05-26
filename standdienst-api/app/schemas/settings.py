from marshmallow import Schema, fields, validate, EXCLUDE
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models import SiteSettings


class SiteSettingsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = SiteSettings
        load_instance = False

    registration_open = fields.Bool(dump_only=True)


class SiteSettingsUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    site_title = fields.Str(validate=validate.Length(min=1, max=200))
    primary_color = fields.Str(allow_none=True, validate=validate.Regexp(r'^(#[0-9a-fA-F]{6})?$'))
    mail_sender_name = fields.Str(validate=validate.Length(max=200))
    shifts_enabled = fields.Bool()
    food_donations_enabled = fields.Bool()
    site_locked = fields.Bool()
    lock_message = fields.Str(allow_none=True)
    log_retention_months = fields.Int(validate=validate.Range(min=1, max=36))
    instance_impressum_html = fields.Str(allow_none=True)
    privacy_policy_html = fields.Str(allow_none=True)
    registration_deadline = fields.DateTime(allow_none=True)
    unregister_deadline_hours = fields.Int(allow_none=True, validate=validate.Range(min=1, max=168))
