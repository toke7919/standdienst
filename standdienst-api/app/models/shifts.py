from datetime import datetime, timezone
from ..extensions import db


class Stand(db.Model):
    __tablename__ = 'stands'

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(
        db.Integer, db.ForeignKey('instances.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), default='')
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))

    shifts = db.relationship(
        'Shift', backref='stand', lazy='dynamic', cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Stand {self.name}>'


class EventDate(db.Model):
    __tablename__ = 'event_dates'

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(
        db.Integer, db.ForeignKey('instances.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    date = db.Column(db.Date, nullable=False, index=True)
    label = db.Column(db.String(100), default='')
    is_draft = db.Column(db.Boolean, nullable=False, default=False)

    shifts = db.relationship(
        'Shift', backref='event_date', lazy='dynamic', cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.UniqueConstraint('instance_id', 'date', name='uq_event_date_instance'),
    )

    @property
    def formatted(self) -> str:
        weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag',
                    'Freitag', 'Samstag', 'Sonntag']
        d = self.date
        return f'{weekdays[d.weekday()]}, {d.strftime("%d.%m.%Y")}'

    def __repr__(self):
        return f'<EventDate {self.date}>'


class Shift(db.Model):
    __tablename__ = 'shifts'

    id = db.Column(db.Integer, primary_key=True)
    stand_id = db.Column(
        db.Integer, db.ForeignKey('stands.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    event_date_id = db.Column(
        db.Integer, db.ForeignKey('event_dates.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    max_volunteers = db.Column(db.Integer, nullable=False, default=2)

    registrations = db.relationship(
        'Registration', backref='shift', lazy='dynamic', cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.UniqueConstraint(
            'stand_id', 'event_date_id', 'start_time', 'end_time',
            name='uq_shift_slot',
        ),
    )

    @property
    def time_range(self) -> str:
        return f'{self.start_time.strftime("%H:%M")} – {self.end_time.strftime("%H:%M")}'

    @property
    def current_count(self) -> int:
        return self.registrations.count()

    @property
    def is_full(self) -> bool:
        return self.current_count >= self.max_volunteers

    @property
    def spots_left(self) -> int:
        return max(0, self.max_volunteers - self.current_count)

    def __repr__(self):
        return f'<Shift {self.stand.name} {self.time_range}>'


class Registration(db.Model):
    __tablename__ = 'registrations'

    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(
        db.Integer, db.ForeignKey('volunteers.id', ondelete='CASCADE'),
        nullable=True, index=True,
    )
    guest_name = db.Column(db.String(100), nullable=True)
    shift_id = db.Column(
        db.Integer, db.ForeignKey('shifts.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    registered_at = db.Column(db.DateTime(timezone=True),
                              default=lambda: datetime.now(timezone.utc))
    registered_by_admin = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint('volunteer_id', 'shift_id', name='uq_volunteer_shift'),
    )

    def __repr__(self):
        return f'<Registration volunteer={self.volunteer_id} shift={self.shift_id}>'
