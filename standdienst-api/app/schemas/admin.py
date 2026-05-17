from marshmallow import Schema, fields, validate, validates, ValidationError
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models import Admin


class AdminSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Admin
        load_instance = False
        exclude = ('password_hash', 'totp_secret', 'reset_token', 'reset_token_expires')


class AdminCreateSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    is_primary = fields.Bool(load_default=False)


class AdminUpdateSchema(Schema):
    email = fields.Email()
    password = fields.Str(validate=validate.Length(min=8))
    is_primary = fields.Bool()
