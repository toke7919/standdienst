from flask import g

from . import admin_bp
from ...models import (
    Volunteer, Stand, Shift, Registration, FoodDonation, FoodDonationType,
    EventDate, Instance, ActivityLog,
)
from ...utils.auth import require_staff, require_admin
from ...utils.responses import ok


@admin_bp.route('/<slug>/dashboard', methods=['GET'])
@require_staff
def dashboard(slug):
    return ok(_instance_stats(g.instance.id))


@admin_bp.route('/dashboard/global', methods=['GET'])
@require_admin
def global_dashboard():
    instances = Instance.query.filter_by(is_active=True).all()
    instance_ids = [i.id for i in instances]

    total_volunteers = Volunteer.query.filter(
        Volunteer.instance_id.in_(instance_ids), Volunteer.deleted_at.is_(None)
    ).count() if instance_ids else 0

    total_shifts = (Shift.query
                    .join(Stand)
                    .filter(Stand.instance_id.in_(instance_ids))
                    .count()) if instance_ids else 0

    total_registrations = (Registration.query
                           .join(Shift)
                           .join(Stand)
                           .filter(Stand.instance_id.in_(instance_ids))
                           .count()) if instance_ids else 0

    total_food = (FoodDonation.query
                  .join(FoodDonationType)
                  .filter(FoodDonationType.instance_id.in_(instance_ids))
                  .count()) if instance_ids else 0

    instance_stats = [
        {'id': i.id, 'name': i.name, 'slug': i.slug, **_instance_stats(i.id)}
        for i in instances
    ]

    recent = (ActivityLog.query
              .filter(ActivityLog.instance_id.is_(None))
              .order_by(ActivityLog.timestamp.desc())
              .limit(10)
              .all())

    return ok({
        'instance_count': len(instances),
        'total_volunteers': total_volunteers,
        'total_shifts': total_shifts,
        'total_registrations': total_registrations,
        'total_food_donations': total_food,
        'instances': instance_stats,
        'recent_activity': [_log_dict(e) for e in recent],
    })


def _instance_stats(instance_id: int) -> dict:
    volunteers = Volunteer.query.filter_by(instance_id=instance_id, deleted_at=None).count()
    stands = Stand.query.filter_by(instance_id=instance_id).count()
    dates = EventDate.query.filter_by(instance_id=instance_id).count()

    shifts_all = (Shift.query.join(Stand).filter(Stand.instance_id == instance_id).all())
    shifts = len(shifts_all)
    shifts_full = sum(1 for s in shifts_all if s.is_full)
    fill_rate = round(shifts_full / shifts * 100) if shifts else 0

    registrations = (Registration.query
                     .join(Shift).join(Stand)
                     .filter(Stand.instance_id == instance_id)
                     .count())

    food_donations = (FoodDonation.query
                      .join(FoodDonationType)
                      .filter(FoodDonationType.instance_id == instance_id)
                      .count())

    recent = (ActivityLog.query
              .filter_by(instance_id=instance_id)
              .order_by(ActivityLog.timestamp.desc())
              .limit(10)
              .all())

    return {
        'volunteers': volunteers,
        'stands': stands,
        'dates': dates,
        'shifts': shifts,
        'shifts_full': shifts_full,
        'fill_rate': fill_rate,
        'registrations': registrations,
        'food_donations': food_donations,
        'recent_activity': [_log_dict(e) for e in recent],
    }


def _log_dict(e) -> dict:
    return {
        'id': e.id,
        'event_type': e.event_type,
        'timestamp': e.timestamp.isoformat() if e.timestamp else None,
        'volunteer_name': e.volunteer_name,
        'details': e.details,
    }
