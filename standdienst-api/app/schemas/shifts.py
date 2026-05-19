from marshmallow import Schema, fields, validate
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from ..models import Stand, EventDate, Shift, Registration


class StandSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Stand
        load_instance = False


class StandCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(validate=validate.Length(max=500), load_default='')
    sort_order = fields.Int(load_default=0)


class StandUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=100))
    description = fields.Str(validate=validate.Length(max=500))
    sort_order = fields.Int()


class StandReorderSchema(Schema):
    order = fields.List(fields.Int(), required=True)


class EventDateSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = EventDate
        load_instance = False

    formatted = fields.Str(dump_only=True)


class EventDateCreateSchema(Schema):
    date = fields.Date(required=True)
    label = fields.Str(validate=validate.Length(max=100), load_default='')


class EventDateUpdateSchema(Schema):
    date = fields.Date()
    label = fields.Str(validate=validate.Length(max=100))


class ShiftSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Shift
        load_instance = False

    time_range = fields.Str(dump_only=True)
    current_count = fields.Int(dump_only=True)
    spots_left = fields.Int(dump_only=True)
    is_full = fields.Bool(dump_only=True)
    stand_name = fields.Method('_stand_name', dump_only=True)
    date_formatted = fields.Method('_date_formatted', dump_only=True)

    def _stand_name(self, obj):
        return obj.stand.name if obj.stand else None

    def _date_formatted(self, obj):
        return obj.event_date.formatted if obj.event_date else None


class ShiftCreateSchema(Schema):
    stand_id = fields.Int(required=True)
    event_date_id = fields.Int(required=True)
    start_time = fields.Time(required=True)
    end_time = fields.Time(required=True)
    max_volunteers = fields.Int(load_default=2, validate=validate.Range(min=1))


class ShiftUpdateSchema(Schema):
    start_time = fields.Time()
    end_time = fields.Time()
    max_volunteers = fields.Int(validate=validate.Range(min=1))


class RegistrationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Registration
        load_instance = False

    display_name = fields.Method('_display_name', dump_only=True)
    volunteer_email = fields.Method('_volunteer_email', dump_only=True)
    stand_name = fields.Method('_stand_name', dump_only=True)
    date_formatted = fields.Method('_date_formatted', dump_only=True)
    time_range = fields.Method('_time_range', dump_only=True)

    def _display_name(self, obj):
        if obj.volunteer:
            return obj.volunteer.name
        return obj.guest_name or '—'

    def _volunteer_email(self, obj):
        return obj.volunteer.email if obj.volunteer else None

    def _stand_name(self, obj):
        if not obj.shift or not obj.shift.stand:
            return None
        return obj.shift.stand.name

    def _date_formatted(self, obj):
        if not obj.shift or not obj.shift.event_date:
            return None
        return obj.shift.event_date.formatted

    def _time_range(self, obj):
        return obj.shift.time_range if obj.shift else None


class RegistrationCreateSchema(Schema):
    shift_id = fields.Int(required=True)
    guest_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
