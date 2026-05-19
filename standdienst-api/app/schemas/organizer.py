from marshmallow import Schema, fields, validate, EXCLUDE
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models import Organizer


class OrganizerSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Organizer
        load_instance = False
        exclude = ('password_hash', 'totp_secret', 'reset_token', 'reset_token_expires')

    has_login = fields.Bool(dump_only=True)
    instance_ids = fields.Method('_instance_ids', dump_only=True)

    def _instance_ids(self, obj):
        return [i.id for i in obj.instances.all()]


class OrganizerCreateSchema(Schema):
    first_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    last_name = fields.Str(validate=validate.Length(max=50), load_default='')
    email = fields.Email(required=True)
    password = fields.Str(validate=validate.Length(min=8), allow_none=True, load_default=None)
    is_instance_admin = fields.Bool(load_default=False)
    instance_ids = fields.List(fields.Int(), load_default=[])


class OrganizerUpdateSchema(Schema):
    first_name = fields.Str(validate=validate.Length(min=1, max=50))
    last_name = fields.Str(validate=validate.Length(max=50))
    email = fields.Email()
    password = fields.Str(validate=validate.Length(min=8), allow_none=True)
    is_instance_admin = fields.Bool()
    instance_ids = fields.List(fields.Int())


class OrganizerInstanceAssignSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    instance_id = fields.Int(required=True)
    is_primary = fields.Bool(load_default=False)
