import re
from marshmallow import Schema, fields, validate, validates, ValidationError, EXCLUDE
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models import Instance, GlobalSettings, MailSettings


class InstanceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Instance
        load_instance = False
        exclude = ()


class InstanceCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    slug = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    is_active = fields.Bool(load_default=True)
    contact_organisation = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_person = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_street = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_zip_city = fields.Str(validate=validate.Length(max=100), allow_none=True)
    contact_email = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_phone = fields.Str(validate=validate.Length(max=50), allow_none=True)

    @validates('slug')
    def validate_slug(self, value, **_):
        if not re.match(r'^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$', value):
            raise ValidationError(
                'Slug: nur Kleinbuchstaben, Ziffern und Bindestriche (mind. 3 Zeichen)'
            )


class InstanceUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(validate=validate.Length(min=1, max=100))
    is_active = fields.Bool()
    contact_organisation = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_person = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_street = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_zip_city = fields.Str(validate=validate.Length(max=100), allow_none=True)
    contact_email = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_phone = fields.Str(validate=validate.Length(max=50), allow_none=True)


class GlobalSettingsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = GlobalSettings
        load_instance = False


class GlobalSettingsUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    base_url = fields.Str(validate=validate.Length(max=500), allow_none=True)
    copyright_text = fields.Str(validate=validate.Length(max=500), allow_none=True)
    provider_impressum_html = fields.Str(allow_none=True)
    impressum_template_html = fields.Str(allow_none=True)
    datenschutz_template_html = fields.Str(allow_none=True)
    contact_organisation = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_person = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_street = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_zip_city = fields.Str(validate=validate.Length(max=100), allow_none=True)
    contact_email = fields.Str(validate=validate.Length(max=200), allow_none=True)
    contact_phone = fields.Str(validate=validate.Length(max=50), allow_none=True)
    log_retention_months = fields.Int(validate=validate.Range(min=1, max=36))
    volunteer_retention_months = fields.Int(validate=validate.Range(min=1, max=120), allow_none=True)
    timezone = fields.Str(validate=validate.Length(max=100))
    github_pat = fields.Str(validate=validate.Length(max=500), allow_none=True)
    github_repo = fields.Str(validate=validate.Length(max=200), allow_none=True)
    ip_whitelist = fields.Str(allow_none=True)


class MailSettingsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = MailSettings
        load_instance = False
        exclude = ('mail_password',)


class MailSettingsUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    mail_server = fields.Str(validate=validate.Length(max=200))
    mail_port = fields.Int(validate=validate.Range(min=1, max=65535))
    mail_use_tls = fields.Bool()
    mail_username = fields.Str(validate=validate.Length(max=200))
    mail_password = fields.Str(validate=validate.Length(max=500))
    mail_default_sender = fields.Str(validate=validate.Length(max=200))
    mail_sender_name = fields.Str(validate=validate.Length(max=200))
