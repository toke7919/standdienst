from marshmallow import Schema, fields, validate, EXCLUDE
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models import Admin


class AdminSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Admin
        load_instance = False
        exclude = ('password_hash', 'totp_secret', 'reset_token', 'reset_token_expires')


class AdminCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    first_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    last_name = fields.Str(validate=validate.Length(max=50), load_default='')
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    is_primary = fields.Bool(load_default=False)


class AdminUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    first_name = fields.Str(validate=validate.Length(min=1, max=50))
    last_name = fields.Str(validate=validate.Length(max=50))
    email = fields.Email()
    password = fields.Str(validate=validate.Length(min=8))
    is_primary = fields.Bool()
