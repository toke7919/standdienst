from marshmallow import Schema, fields, validate
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models import Volunteer


class VolunteerSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Volunteer
        load_instance = False
        exclude = ('password_hash', 'reset_token', 'reset_token_expires')

    is_deleted = fields.Bool(dump_only=True)
    has_login = fields.Bool(dump_only=True)


class VolunteerCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(allow_none=True, load_default=None)
    password = fields.Str(validate=validate.Length(min=8), allow_none=True, load_default=None)


class VolunteerUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=100))
    email = fields.Email(allow_none=True)
    password = fields.Str(validate=validate.Length(min=8), allow_none=True)


class VolunteerRegisterSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    captcha_answer = fields.Int(required=True)
    consent = fields.Bool(required=True)
