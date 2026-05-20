from datetime import datetime, timezone
from ..extensions import db


class FoodDonationType(db.Model):
    __tablename__ = 'food_donation_types'

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(
        db.Integer, db.ForeignKey('instances.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    event_date_id = db.Column(
        db.Integer, db.ForeignKey('event_dates.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    refrigeration_enabled = db.Column(db.Boolean, nullable=False, default=False)
    delivery_datetime = db.Column(db.DateTime(timezone=True), nullable=True)
    delivery_location = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))

    event_date = db.relationship('EventDate',
                                 backref=db.backref('food_types', lazy='dynamic'))
    donations = db.relationship(
        'FoodDonation', backref='food_type', lazy='dynamic', cascade='all, delete-orphan'
    )

    @property
    def donation_count(self) -> int:
        return self.donations.count()

    def __repr__(self):
        return f'<FoodDonationType {self.name}>'


class FoodDonation(db.Model):
    __tablename__ = 'food_donations'

    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(
        db.Integer, db.ForeignKey('volunteers.id', ondelete='SET NULL'),
        nullable=True, index=True,
    )
    food_type_id = db.Column(
        db.Integer, db.ForeignKey('food_donation_types.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    guest_name = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(100), nullable=False)
    needs_refrigeration = db.Column(db.Boolean, default=False, nullable=False)
    registered_at = db.Column(db.DateTime(timezone=True),
                              default=lambda: datetime.now(timezone.utc))

    volunteer = db.relationship(
        'Volunteer',
        backref=db.backref('food_donations', lazy='dynamic', cascade='all, delete-orphan'),
    )

    def __repr__(self):
        return f'<FoodDonation volunteer={self.volunteer_id} type={self.food_type_id}>'
