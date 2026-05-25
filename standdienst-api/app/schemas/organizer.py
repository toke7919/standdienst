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
    instance_admin_ids = fields.Method('_instance_admin_ids', dump_only=True)

    def _instance_ids(self, obj):
        return [i.id for i in obj.instances.all()]

    def _instance_admin_ids(self, obj):
        from ..models.instance import organizer_instances
        from ..extensions import db
        rows = db.session.execute(
            organizer_instances.select().where(
                organizer_instances.c.organizer_id == obj.id,
                organizer_instances.c.is_instance_admin == True,
            )
        ).fetchall()
        return [row.instance_id for row in rows]


class OrganizerCreateSchema(Schema):
    first_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    last_name = fields.Str(validate=validate.Length(max=50), load_default='')
    email = fields.Email(required=True)
    password = fields.Str(validate=validate.Length(min=8), allow_none=True, load_default=None)
    instance_ids = fields.List(fields.Int(), load_default=[])
    instance_admin_ids = fields.List(fields.Int(), load_default=[])


class OrganizerUpdateSchema(Schema):
    first_name = fields.Str(validate=validate.Length(min=1, max=50))
    last_name = fields.Str(validate=validate.Length(max=50))
    email = fields.Email()
    password = fields.Str(validate=validate.Length(min=8), allow_none=True)
    instance_ids = fields.List(fields.Int())
    instance_admin_ids = fields.List(fields.Int())


class OrganizerInstanceAssignSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    instance_id = fields.Int(required=True)
    is_primary = fields.Bool(load_default=False)
