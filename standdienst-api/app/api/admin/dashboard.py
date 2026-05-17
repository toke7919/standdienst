from flask import g

from . import admin_bp
from ...models import Volunteer, Stand, Shift, Registration, FoodDonation, FoodDonationType, EventDate
from ...utils.auth import require_staff
from ...utils.responses import ok


@admin_bp.route('/<slug>/dashboard', methods=['GET'])
@require_staff
def dashboard(slug):
    instance_id = g.instance.id
    return ok(_build_stats(instance_id))


def _build_stats(instance_id: int) -> dict:
    volunteer_count = Volunteer.query.filter_by(
        instance_id=instance_id, deleted_at=None
    ).count()

    stand_count = Stand.query.filter_by(instance_id=instance_id).count()

    date_count = EventDate.query.filter_by(instance_id=instance_id).count()

    shift_count = (Shift.query
                   .join(Stand)
                   .filter(Stand.instance_id == instance_id)
                   .count())

    reg_count = (Registration.query
                 .join(Shift)
                 .join(Stand)
                 .filter(Stand.instance_id == instance_id)
                 .count())

    food_count = (FoodDonation.query
                  .join(FoodDonationType)
                  .filter(FoodDonationType.instance_id == instance_id)
                  .count())

    shifts_full = (Shift.query
                   .join(Stand)
                   .filter(Stand.instance_id == instance_id)
                   .all())
    full_count = sum(1 for s in shifts_full if s.is_full)

    return {
        'volunteers': volunteer_count,
        'stands': stand_count,
        'dates': date_count,
        'shifts': shift_count,
        'registrations': reg_count,
        'food_donations': food_count,
        'shifts_full': full_count,
    }
