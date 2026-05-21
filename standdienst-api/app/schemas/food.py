from marshmallow import Schema, fields, validate, EXCLUDE
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models import FoodDonationType, FoodDonation


class FoodDonationTypeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = FoodDonationType
        load_instance = False

    donation_count = fields.Int(dump_only=True)


class FoodDonationTypeCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    event_date_id = fields.Int(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    refrigeration_enabled = fields.Bool(load_default=False)
    delivery_datetime = fields.DateTime(allow_none=True, load_default=None)
    delivery_location = fields.Str(validate=validate.Length(max=200), allow_none=True, load_default=None)
    notes = fields.Str(allow_none=True, load_default=None)


class FoodDonationTypeUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(validate=validate.Length(min=1, max=100))
    refrigeration_enabled = fields.Bool()
    delivery_datetime = fields.DateTime(allow_none=True)
    delivery_location = fields.Str(validate=validate.Length(max=200), allow_none=True)
    notes = fields.Str(allow_none=True)


class FoodDonationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = FoodDonation
        load_instance = False
        include_fk = True

    volunteer_name = fields.Method('_volunteer_name', dump_only=True)
    food_type_name = fields.Method('_food_type_name', dump_only=True)
    by_admin = fields.Method('_by_admin', dump_only=True)

    def _volunteer_name(self, obj):
        if obj.volunteer:
            return obj.volunteer.name
        return obj.guest_name

    def _food_type_name(self, obj):
        return obj.food_type.name if obj.food_type else None

    def _by_admin(self, obj):
        return obj.guest_name is not None


class FoodDonationCreateSchema(Schema):
    food_type_id = fields.Int(required=True)
    description = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    needs_refrigeration = fields.Bool(load_default=False)


class FoodDonationAdminCreateSchema(Schema):
    guest_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    food_type_id = fields.Int(required=True)
    description = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    needs_refrigeration = fields.Bool(load_default=False)


class FoodDonationAdminUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    guest_name = fields.Str(validate=validate.Length(min=1, max=100))
    description = fields.Str(validate=validate.Length(min=1, max=100))
    needs_refrigeration = fields.Bool()
