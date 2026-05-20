from datetime import date as _date, timedelta
from flask import g
from sqlalchemy import func

from . import admin_bp
from ...models import (
    Volunteer, Stand, Shift, Registration, FoodDonation, FoodDonationType,
    EventDate, Instance, ActivityLog,
)
from ...utils.auth import require_staff, require_admin
from ...utils.responses import ok


_ORGANIZER_TYPES = [
    'shift_register', 'shift_unregister',
    'food_register', 'food_unregister',
]


@admin_bp.route('/<slug>/dashboard', methods=['GET'])
@require_staff
def dashboard(slug):
    # recent_activity im Dashboard immer auf operative Typen filtern (Punkt 9)
    return ok(_instance_stats(g.instance.id, event_types=_ORGANIZER_TYPES))


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
              .filter(ActivityLog.event_type.in_(_ORGANIZER_TYPES))
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


def _instance_stats(instance_id: int, event_types=None) -> dict:
    volunteers = Volunteer.query.filter_by(instance_id=instance_id, deleted_at=None).count()

    shifts_all = (Shift.query.join(Stand).filter(Stand.instance_id == instance_id).all())
    shifts = len(shifts_all)
    shifts_full = sum(1 for s in shifts_all if s.is_full)
    shifts_empty = sum(1 for s in shifts_all if s.current_count == 0)
    shifts_free = shifts - shifts_full
    fill_rate = round(shifts_full / shifts * 100) if shifts else 0

    registrations = (Registration.query
                     .join(Shift).join(Stand)
                     .filter(Stand.instance_id == instance_id)
                     .count())

    # Helfer ohne Schicht: aktive Volunteers mit 0 Anmeldungen
    volunteers_with_shift = (Registration.query
                             .join(Shift).join(Stand)
                             .filter(Stand.instance_id == instance_id,
                                     Registration.volunteer_id.isnot(None))
                             .with_entities(Registration.volunteer_id)
                             .distinct()
                             .count())
    volunteers_registered = (Volunteer.query
                              .filter_by(instance_id=instance_id, deleted_at=None)
                              .filter(Volunteer.email.isnot(None))
                              .count())
    volunteers_without_shift = max(0, volunteers_registered - volunteers_with_shift)

    food_donations = (FoodDonation.query
                      .join(FoodDonationType)
                      .filter(FoodDonationType.instance_id == instance_id)
                      .count())

    # Auslastung je Termin
    dates_all = EventDate.query.filter_by(instance_id=instance_id).order_by(EventDate.date).all()
    dates_fill = []
    for d in dates_all:
        d_shifts = [s for s in shifts_all if s.event_date_id == d.id]
        d_total = len(d_shifts)
        d_full = sum(1 for s in d_shifts if s.is_full)
        d_rate = round(d_full / d_total * 100) if d_total else 0
        dates_fill.append({
            'date_id': d.id,
            'date_formatted': d.formatted,
            'shifts': d_total,
            'shifts_full': d_full,
            'fill_rate': d_rate,
        })

    # Gesamtkapazität (Summe aller Plätze über alle Schichten)
    total_spots = sum(s.max_volunteers for s in shifts_all)

    # Anmeldungen der letzten 7 Tage (für Trend-Sparkline)
    today = _date.today()
    seven_days_ago = today - timedelta(days=6)
    _day_names = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    daily_q = (Registration.query
               .join(Shift).join(Stand)
               .filter(Stand.instance_id == instance_id,
                       func.date(Registration.registered_at) >= seven_days_ago)
               .with_entities(func.date(Registration.registered_at).label('day'),
                              func.count().label('cnt'))
               .group_by(func.date(Registration.registered_at))
               .all())
    daily_map = {}
    for r in daily_q:
        key = r.day.isoformat() if hasattr(r.day, 'isoformat') else str(r.day)
        daily_map[key] = r.cnt
    daily_registrations = [
        {
            'date': (seven_days_ago + timedelta(days=i)).isoformat(),
            'day_short': _day_names[(seven_days_ago + timedelta(days=i)).weekday()],
            'count': daily_map.get((seven_days_ago + timedelta(days=i)).isoformat(), 0),
        }
        for i in range(7)
    ]

    # Nächster anstehender Termin
    next_event = None
    upcoming = [d for d in dates_all if d.date >= today]
    if upcoming:
        n = upcoming[0]
        next_event = {
            'date_formatted': n.formatted,
            'days_until': (n.date - today).days,
        }

    recent_q = ActivityLog.query.filter_by(instance_id=instance_id)
    if event_types is not None:
        recent_q = recent_q.filter(ActivityLog.event_type.in_(event_types))
    recent = (recent_q
              .order_by(ActivityLog.timestamp.desc())
              .limit(10)
              .all())

    return {
        'volunteers': volunteers,
        'shifts': shifts,
        'shifts_full': shifts_full,
        'shifts_free': shifts_free,
        'shifts_empty': shifts_empty,
        'fill_rate': fill_rate,
        'registrations': registrations,
        'volunteers_without_shift': volunteers_without_shift,
        'food_donations': food_donations,
        'total_spots': total_spots,
        'daily_registrations': daily_registrations,
        'next_event': next_event,
        'dates_fill': dates_fill,
        'recent_activity': [_log_dict(e) for e in recent],
    }


def _log_dict(e) -> dict:
    return {
        'id': e.id,
        'event_type': e.event_type,
        'timestamp': e.timestamp.isoformat() if e.timestamp else None,
        'volunteer_name': e.volunteer_name,
        'details': e.details,
        'instance_id': e.instance_id,
    }
