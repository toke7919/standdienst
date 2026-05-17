from marshmallow import Schema, fields, validate
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models import FoodDonationType, FoodDonation


class FoodDonationTypeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = FoodDonationType
        load_instance = False

    donation_count = fields.Int(dump_only=True)


class FoodDonationTypeCreateSchema(Schema):
    event_date_id = fields.Int(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    delivery_datetime = fields.DateTime(allow_none=True, load_default=None)
    delivery_location = fields.Str(validate=validate.Length(max=200), allow_none=True, load_default=None)
    notes = fields.Str(allow_none=True, load_default=None)


class FoodDonationTypeUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=100))
    delivery_datetime = fields.DateTime(allow_none=True)
    delivery_location = fields.Str(validate=validate.Length(max=200), allow_none=True)
    notes = fields.Str(allow_none=True)


class FoodDonationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = FoodDonation
        load_instance = False

    volunteer_name = fields.Method('_volunteer_name', dump_only=True)
    food_type_name = fields.Method('_food_type_name', dump_only=True)

    def _volunteer_name(self, obj):
        return obj.volunteer.name if obj.volunteer else None

    def _food_type_name(self, obj):
        return obj.food_type.name if obj.food_type else None


class FoodDonationCreateSchema(Schema):
    food_type_id = fields.Int(required=True)
    description = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    needs_refrigeration = fields.Bool(load_default=False)


class FoodDonationAdminCreateSchema(Schema):
    volunteer_id = fields.Int(required=True)
    food_type_id = fields.Int(required=True)
    description = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    needs_refrigeration = fields.Bool(load_default=False)
