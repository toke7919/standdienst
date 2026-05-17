from marshmallow import Schema, fields, validate, validates, ValidationError
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
    date = fields.Method('_date', dump_only=True)

    def _stand_name(self, obj):
        return obj.stand.name if obj.stand else None

    def _date(self, obj):
        return str(obj.event_date.date) if obj.event_date else None


class ShiftCreateSchema(Schema):
    stand_id = fields.Int(required=True)
    event_date_id = fields.Int(required=True)
    start_time = fields.Time(required=True)
    end_time = fields.Time(required=True)
    max_volunteers = fields.Int(load_default=2, validate=validate.Range(min=1))

    @validates('end_time')
    def validate_times(self, value):
        pass  # Cross-field validation done in route handler


class ShiftUpdateSchema(Schema):
    start_time = fields.Time()
    end_time = fields.Time()
    max_volunteers = fields.Int(validate=validate.Range(min=1))


class RegistrationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Registration
        load_instance = False

    volunteer_name = fields.Method('_volunteer_name', dump_only=True)
    volunteer_email = fields.Method('_volunteer_email', dump_only=True)
    shift_info = fields.Method('_shift_info', dump_only=True)

    def _volunteer_name(self, obj):
        return obj.volunteer.name if obj.volunteer else None

    def _volunteer_email(self, obj):
        return obj.volunteer.email if obj.volunteer else None

    def _shift_info(self, obj):
        if not obj.shift:
            return None
        s = obj.shift
        return {
            'stand': s.stand.name if s.stand else None,
            'time_range': s.time_range,
            'date': str(s.event_date.date) if s.event_date else None,
        }


class RegistrationCreateSchema(Schema):
    volunteer_id = fields.Int(required=True)
    shift_id = fields.Int(required=True)
