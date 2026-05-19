import json
import time as _time
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g, current_app, Response, stream_with_context
from flask_jwt_extended import create_access_token, create_refresh_token
from marshmallow import ValidationError

from ..extensions import db, limiter
from ..models import (
    Instance, Stand, EventDate, Shift, Registration,
    FoodDonationType, FoodDonation, ActivityLog, Volunteer,
)
from ..schemas.shifts import ShiftSchema, RegistrationSchema
from ..schemas.food import FoodDonationSchema, FoodDonationCreateSchema
from ..utils.auth import require_volunteer, validate_password_strength
from ..utils.mail import is_mail_configured, send_mail, build_daten_auskunft_email
from ..utils.responses import ok, created, no_content, error, optimistic_lock_conflict
from ..utils.settings_cache import get_site_settings

volunteer_bp = Blueprint('volunteer', __name__)

_shift_schema = ShiftSchema(many=True)
_reg_schema = RegistrationSchema(many=True)
_food_schema = FoodDonationSchema(many=True)
_food_create_schema = FoodDonationCreateSchema()


# ---------------------------------------------------------------------------
# Schichten
# ---------------------------------------------------------------------------

@volunteer_bp.route('/<slug>/shifts/events', methods=['GET'])
@require_volunteer
def shift_events(slug):
    """SSE-Endpunkt: liefert Echtzeit-Aktualisierungen wenn Schichten belegt/freigegeben werden."""
    uri = current_app.config.get('RATELIMIT_STORAGE_URI', 'memory://')
    if not uri.startswith('redis://'):
        # Ohne Redis: einmaliges Event senden und Verbindung schließen
        return Response('data: {"type":"unavailable"}\n\n',
                        content_type='text/event-stream',
                        headers={'Cache-Control': 'no-cache'})

    def generate():
        import redis as redis_lib
        r = redis_lib.from_url(uri, socket_connect_timeout=2)
        pubsub = r.pubsub()
        pubsub.subscribe(f'shifts:{slug}')
        deadline = _time.monotonic() + 25
        try:
            yield 'data: {"type":"connected"}\n\n'
            while _time.monotonic() < deadline:
                msg = pubsub.get_message(timeout=1.0)
                if msg and msg['type'] == 'message':
                    data = msg['data']
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield f'data: {data}\n\n'
        finally:
            try:
                pubsub.close()
                r.close()
            except Exception:
                pass

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@volunteer_bp.route('/<slug>/shifts', methods=['GET'])
@require_volunteer
def list_shifts(slug):
    instance = g.instance
    settings = get_site_settings(instance.id)
    if settings and not settings.shifts_enabled:
        return error('Schichten sind deaktiviert', 403)

    dates = EventDate.query.filter_by(instance_id=instance.id).order_by(EventDate.date).all()
    result = []
    for date in dates:
        stands = Stand.query.filter_by(instance_id=instance.id).order_by(Stand.sort_order).all()
        for stand in stands:
            shifts = Shift.query.filter_by(
                stand_id=stand.id, event_date_id=date.id
            ).order_by(Shift.start_time).all()
            for shift in shifts:
                is_registered = Registration.query.filter_by(
                    volunteer_id=g.current_user.id, shift_id=shift.id
                ).first() is not None
                result.append({
                    **ShiftSchema().dump(shift),
                    'is_registered': is_registered,
                })
    return ok(result)


@volunteer_bp.route('/<slug>/shifts/<int:shift_id>/register', methods=['POST'])
@limiter.limit('30 per minute')
@require_volunteer
def register_shift(slug, shift_id):
    settings = get_site_settings(g.instance.id)
    if settings and not settings.registration_open:
        return error('Anmeldeschluss ist überschritten', 403)

    # Row-Level Lock: sperrt Schicht-Zeile für Dauer der Transaktion
    shift = Shift.query.with_for_update().get(shift_id)
    if not shift:
        return error('Schicht nicht gefunden', 404)
    stand = Stand.query.get(shift.stand_id)
    if not stand or stand.instance_id != g.instance.id:
        return error('Schicht nicht gefunden', 404)

    if shift.is_full:
        return error('Schicht ist bereits voll', 409)
    if Registration.query.filter_by(volunteer_id=g.current_user.id, shift_id=shift_id).first():
        return error('Bereits eingetragen', 409)
    if _has_time_overlap(g.current_user.id, shift):
        return error('Zeitüberschneidung mit einer anderen Schicht', 409)

    db.session.add(Registration(volunteer_id=g.current_user.id, shift_id=shift_id))
    db.session.add(_activity(g.instance.id, ActivityLog.SHIFT_REGISTER, g.current_user,
                             details=f'shift_id={shift_id}'))
    db.session.commit()
    _publish_shift_update(current_app, slug, shift_id)
    return created({'shift_id': shift_id})


@volunteer_bp.route('/<slug>/shifts/<int:shift_id>/register', methods=['DELETE'])
@limiter.limit('30 per minute')
@require_volunteer
def unregister_shift(slug, shift_id):
    reg = Registration.query.filter_by(
        volunteer_id=g.current_user.id, shift_id=shift_id
    ).first()
    if not reg:
        return error('Nicht eingetragen', 404)

    db.session.delete(reg)
    db.session.add(_activity(g.instance.id, ActivityLog.SHIFT_UNREGISTER, g.current_user,
                             details=f'shift_id={shift_id}'))
    db.session.commit()
    _publish_shift_update(current_app, slug, shift_id)
    return no_content()


@volunteer_bp.route('/<slug>/my-registrations', methods=['GET'])
@require_volunteer
def my_registrations(slug):
    regs = Registration.query.filter_by(volunteer_id=g.current_user.id).all()
    return ok(_reg_schema.dump(regs))


@volunteer_bp.route('/<slug>/my-registrations/ical', methods=['GET'])
@require_volunteer
def my_registrations_ical(slug):
    from datetime import date
    from icalendar import Calendar, Event as IEvent
    import io
    from flask import send_file
    import pytz

    cal = Calendar()
    cal.add('prodid', f'-//Standdienst//{g.instance.slug}//DE')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', f'Meine Schichten – {g.instance.name}')

    tz = pytz.timezone('Europe/Berlin')
    regs = Registration.query.filter_by(volunteer_id=g.current_user.id).all()

    for reg in regs:
        shift = reg.shift
        event = IEvent()
        event.add('summary', f'Standdienst: {shift.stand.name}')
        event.add('dtstart', tz.localize(
            datetime.combine(shift.event_date.date, shift.start_time)
        ))
        event.add('dtend', tz.localize(
            datetime.combine(shift.event_date.date, shift.end_time)
        ))
        event.add('uid', f'vol-{reg.id}@standdienst')
        cal.add_component(event)

    buf = io.BytesIO(cal.to_ical())
    filename = f'meine-schichten-{g.instance.slug}.ics'
    return send_file(buf, mimetype='text/calendar', as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# Essensspenden
# ---------------------------------------------------------------------------

@volunteer_bp.route('/<slug>/food-donations', methods=['GET'])
@require_volunteer
def list_food_donations(slug):
    settings = get_site_settings(g.instance.id)
    if settings and not settings.food_donations_enabled:
        return error('Essensspenden sind deaktiviert', 403)

    donations = FoodDonation.query.filter_by(volunteer_id=g.current_user.id).all()
    return ok(_food_schema.dump(donations))


@volunteer_bp.route('/<slug>/food-donations', methods=['POST'])
@limiter.limit('20 per minute')
@require_volunteer
def create_food_donation(slug):
    settings = get_site_settings(g.instance.id)
    if settings and not settings.registration_open:
        return error('Anmeldeschluss ist überschritten', 403)

    try:
        data = _food_create_schema.load(request.get_json() or {})
    except ValidationError as e:
        return error('Validierungsfehler', 422, e.messages)

    food_type = FoodDonationType.query.filter_by(
        id=data['food_type_id'], instance_id=g.instance.id
    ).first()
    if not food_type:
        return error('Essenspendenart nicht gefunden', 404)

    donation = FoodDonation(volunteer_id=g.current_user.id, **data)
    db.session.add(donation)
    db.session.add(_activity(g.instance.id, ActivityLog.FOOD_REGISTER, g.current_user,
                             details=f'food_type_id={data["food_type_id"]}'))
    db.session.commit()
    return created(FoodDonationSchema().dump(donation))


@volunteer_bp.route('/<slug>/food-donations/<int:donation_id>', methods=['DELETE'])
@require_volunteer
def delete_food_donation(slug, donation_id):
    donation = FoodDonation.query.filter_by(
        id=donation_id, volunteer_id=g.current_user.id
    ).first()
    if not donation:
        return error('Essensspende nicht gefunden', 404)

    db.session.delete(donation)
    db.session.add(_activity(g.instance.id, ActivityLog.FOOD_UNREGISTER, g.current_user,
                             details=f'donation_id={donation_id}'))
    db.session.commit()
    return no_content()


# ---------------------------------------------------------------------------
# Profil + DSGVO
# ---------------------------------------------------------------------------

@volunteer_bp.route('/<slug>/profile', methods=['PUT'])
@require_volunteer
def update_profile(slug):
    data = request.get_json() or {}
    volunteer = g.current_user

    if optimistic_lock_conflict(volunteer, data.get('updated_at')):
        return error('Datensatz wurde zwischenzeitlich geändert', 409)

    if 'first_name' in data:
        first = data['first_name'].strip()
        if not first:
            return error('Vorname darf nicht leer sein', 422)
        volunteer.first_name = first
    if 'last_name' in data:
        volunteer.last_name = (data.get('last_name') or '').strip()
    if 'first_name' in data or 'last_name' in data:
        volunteer.name = f'{volunteer.first_name or ""} {volunteer.last_name or ""}'.strip() or volunteer.name
    if 'password' in data and data['password']:
        if not validate_password_strength(data['password'], role='volunteer'):
            return error('Passwort zu schwach (mind. 6 Zeichen)', 400)
        volunteer.set_password(data['password'])
        volunteer.rotate_jwt()

    db.session.commit()
    return ok({
        'name': volunteer.name,
        'first_name': volunteer.first_name,
        'last_name': volunteer.last_name,
        'email': volunteer.email,
        'updated_at': volunteer.updated_at.isoformat() if volunteer.updated_at else None,
    })


@volunteer_bp.route('/<slug>/profile', methods=['DELETE'])
@require_volunteer
def delete_profile(slug):
    g.current_user.soft_delete()
    db.session.commit()
    return no_content()


# ---------------------------------------------------------------------------
# DSGVO – Datenauskunft Art. 20
# ---------------------------------------------------------------------------

@volunteer_bp.route('/<slug>/meine-daten', methods=['GET'])
@require_volunteer
def meine_daten(slug):
    return ok(_build_volunteer_export(g.current_user))


@volunteer_bp.route('/<slug>/meine-daten/export', methods=['POST'])
@limiter.limit('3 per day')
@require_volunteer
def meine_daten_export(slug):
    """Art. 15 DSGVO – Datenauskunft per E-Mail zusenden."""
    v = g.current_user
    if not v.email:
        return error('Keine E-Mail-Adresse hinterlegt', 400)
    if not is_mail_configured():
        return error('E-Mail nicht konfiguriert', 503)

    settings = get_site_settings(g.instance.id)
    title = settings.site_title if settings else g.instance.name
    base_url = current_app.config.get('FRONTEND_URL', '')
    send_mail(v.email, f'Ihre Daten bei {title}',
              build_daten_auskunft_email(v.name, _build_volunteer_export(v), title, base_url),
              sender_name=title)
    return ok({'message': 'Daten wurden an Ihre E-Mail-Adresse gesendet'})


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _build_volunteer_export(v) -> dict:
    """Alle gespeicherten Daten eines Volunteers (Art. 15/20 DSGVO)."""
    registrations = [
        {
            'shift_id': reg.shift.id,
            'stand': reg.shift.stand.name,
            'date': reg.shift.event_date.date.isoformat(),
            'start_time': reg.shift.start_time.isoformat(),
            'end_time': reg.shift.end_time.isoformat(),
            'registered_at': reg.registered_at.isoformat() if reg.registered_at else None,
        }
        for reg in v.registrations
    ]
    food_donations = [
        {
            'food_type': fd.food_type.name,
            'description': fd.description,
            'needs_refrigeration': fd.needs_refrigeration,
            'registered_at': fd.registered_at.isoformat() if fd.registered_at else None,
        }
        for fd in v.food_donations
    ]
    return {
        'volunteer': {
            'id': v.id, 'name': v.name, 'email': v.email,
            'instance_id': v.instance_id,
            'created_at': v.created_at.isoformat() if v.created_at else None,
            'consent_given_at': v.consent_given_at.isoformat() if v.consent_given_at else None,
        },
        'registrations': registrations,
        'food_donations': food_donations,
    }


def _has_time_overlap(volunteer_id: int, new_shift: Shift) -> bool:
    """Prüft ob Volunteer am selben Veranstaltungstag eine überlappende Schicht hat."""
    existing = (
        Registration.query
        .join(Shift, Registration.shift_id == Shift.id)
        .filter(
            Registration.volunteer_id == volunteer_id,
            Shift.event_date_id == new_shift.event_date_id,
            Shift.id != new_shift.id,
        )
        .all()
    )
    for reg in existing:
        s = reg.shift
        if s.start_time < new_shift.end_time and new_shift.start_time < s.end_time:
            return True
    return False


def _publish_shift_update(app, slug: str, shift_id: int) -> None:
    """Benachrichtigt SSE-Clients über eine geänderte Schichtbelegung."""
    uri = app.config.get('RATELIMIT_STORAGE_URI', 'memory://')
    if not uri.startswith('redis://'):
        return
    try:
        import redis as redis_lib
        r = redis_lib.from_url(uri, socket_connect_timeout=2)
        r.publish(f'shifts:{slug}', json.dumps({'shift_id': shift_id}))
        r.close()
    except Exception:
        pass  # SSE ist Best-Effort – Fehler nicht an Client weitergeben


def _activity(instance_id, event_type, user, details=None) -> ActivityLog:
    return ActivityLog(
        instance_id=instance_id,
        event_type=event_type,
        volunteer_name=user.name,
        volunteer_id=user.id,
        ip_address=request.remote_addr,
        actor_type='volunteer',
        details=details,
        user_agent=request.headers.get('User-Agent', '')[:500],
    )
