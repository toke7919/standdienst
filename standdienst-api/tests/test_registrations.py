"""Funktionale Tests für app/api/admin/registrations.py.

Autorisierung (@require_staff für GET, @require_instance_admin für POST/DELETE,
Instanz-Zugriffsschutz) ist bereits in test_authz_registrations.py abgedeckt.
Hier geht es um Statuscode, Response-Form und Geschäftslogik: Filter, das
Grid-Layout, Validierung/Duplikat-Schutz beim Anlegen und die Aktivitätslog-
Details.
"""
from datetime import date, time

from app.extensions import db as _db
from app.models import Stand, EventDate, Shift, Registration, Volunteer, ActivityLog
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


def _make_shift(instance, stand_name='Stand', day=date(2026, 9, 1),
                start=time(10, 0), end=time(12, 0), max_volunteers=2, sort_order=0):
    stand = Stand(instance_id=instance.id, name=stand_name, sort_order=sort_order)
    _db.session.add(stand)
    _db.session.flush()
    ed = _db.session.query(EventDate).filter_by(instance_id=instance.id, date=day).first()
    if not ed:
        ed = EventDate(instance_id=instance.id, date=day, is_draft=False)
        _db.session.add(ed)
        _db.session.flush()
    shift = Shift(stand_id=stand.id, event_date_id=ed.id,
                  start_time=start, end_time=end, max_volunteers=max_volunteers)
    _db.session.add(shift)
    _db.session.commit()
    return shift


# ---------------------------------------------------------------------------
# GET /registrations
# ---------------------------------------------------------------------------

def test_list_registrations_filters_by_shift_id(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift1 = _make_shift(instance, stand_name='A')
    shift2 = _make_shift(instance, stand_name='B')
    _db.session.add_all([
        Registration(shift_id=shift1.id, guest_name='Gast 1'),
        Registration(shift_id=shift2.id, guest_name='Gast 2'),
    ])
    _db.session.commit()

    rv = c.get(f'/api/admin/{instance.slug}/registrations?shift_id={shift1.id}')
    assert rv.status_code == 200
    body = rv.get_json()
    assert body['total'] == 1
    assert body['data'][0]['guest_name'] == 'Gast 1'


def test_list_registrations_filters_by_date_id(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift1 = _make_shift(instance, day=date(2026, 9, 1))
    shift2 = _make_shift(instance, day=date(2026, 9, 2))
    _db.session.add_all([
        Registration(shift_id=shift1.id, guest_name='Gast 1'),
        Registration(shift_id=shift2.id, guest_name='Gast 2'),
    ])
    _db.session.commit()

    rv = c.get(f'/api/admin/{instance.slug}/registrations?date_id={shift1.event_date_id}')
    assert rv.status_code == 200
    assert rv.get_json()['total'] == 1


# ---------------------------------------------------------------------------
# GET /registrations/grid
# ---------------------------------------------------------------------------

def test_registration_grid_empty_state(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.get(f'/api/admin/{instance.slug}/registrations/grid')
    assert rv.status_code == 200
    assert rv.get_json()['data'] == []


def test_registration_grid_structure_with_data(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift_a = _make_shift(instance, stand_name='Grillstand', day=date(2026, 9, 1), sort_order=0)
    shift_b = _make_shift(instance, stand_name='Kasse', day=date(2026, 9, 1),
                          start=time(10, 0), end=time(12, 0), sort_order=1)
    volunteer = Volunteer(instance_id=instance.id, name='Helfer Eins', first_name='Helfer')
    _db.session.add(volunteer)
    _db.session.flush()
    _db.session.add(Registration(shift_id=shift_a.id, volunteer_id=volunteer.id, registered_by_admin=False))
    _db.session.commit()

    rv = c.get(f'/api/admin/{instance.slug}/registrations/grid')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert len(data) == 1  # ein Termin
    day_grid = data[0]
    assert day_grid['is_draft'] is False
    stand_names = {s['name'] for s in day_grid['stands']}
    assert stand_names == {'Grillstand', 'Kasse'}
    # Beide Stände nutzen dieselbe Zeit -> genau eine Zeitzeile
    assert len(day_grid['rows']) == 1
    row = day_grid['rows'][0]
    assert row['time_range'] == '10:00 – 12:00'
    # Zellen in Stand-Reihenfolge (sort_order): Grillstand zuerst
    assert row['cells'][0]['registrations'][0]['name'] == 'Helfer Eins'
    assert row['cells'][0]['registrations'][0]['by_admin'] is False
    assert row['cells'][0]['spots_left'] == 1


def test_registration_grid_marks_empty_cell_when_no_shift_for_stand_and_slot(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    _make_shift(instance, stand_name='Grillstand', day=date(2026, 9, 1), start=time(8, 0), end=time(10, 0))
    _make_shift(instance, stand_name='Kasse', day=date(2026, 9, 1), start=time(10, 0), end=time(12, 0))

    rv = c.get(f'/api/admin/{instance.slug}/registrations/grid')
    day_grid = rv.get_json()['data'][0]
    assert len(day_grid['rows']) == 2  # zwei unterschiedliche Zeitslots
    # In jeder Zeile muss mindestens eine Zelle None sein (Stand hat in diesem Slot keinen Dienst)
    assert any(cell is None for row in day_grid['rows'] for cell in row['cells'])


# ---------------------------------------------------------------------------
# POST /registrations
# ---------------------------------------------------------------------------

def test_create_registration_validation_error(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/registrations', json={})
    assert rv.status_code == 422


def test_create_registration_without_volunteer_or_guest_name_returns_422(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance)
    rv = c.post(f'/api/admin/{instance.slug}/registrations', json={'shift_id': shift.id})
    assert rv.status_code == 422


def test_create_registration_shift_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/{instance.slug}/registrations',
               json={'shift_id': 99999, 'guest_name': 'Gast'})
    assert rv.status_code == 404


def test_create_registration_shift_full_returns_409(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance, max_volunteers=1)
    _db.session.add(Registration(shift_id=shift.id, guest_name='Schon da'))
    _db.session.commit()

    rv = c.post(f'/api/admin/{instance.slug}/registrations',
               json={'shift_id': shift.id, 'guest_name': 'Neuer Gast'})
    assert rv.status_code == 409


def test_create_registration_volunteer_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance)
    rv = c.post(f'/api/admin/{instance.slug}/registrations',
               json={'shift_id': shift.id, 'volunteer_id': 99999})
    assert rv.status_code == 404


def test_create_registration_deleted_volunteer_returns_400(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance)
    volunteer = Volunteer(instance_id=instance.id, name='Wird Geloescht', first_name='Wird')
    _db.session.add(volunteer)
    _db.session.commit()
    volunteer.soft_delete()
    _db.session.commit()

    rv = c.post(f'/api/admin/{instance.slug}/registrations',
               json={'shift_id': shift.id, 'volunteer_id': volunteer.id})
    assert rv.status_code == 400


def test_create_registration_with_guest_name_success(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance)
    rv = c.post(f'/api/admin/{instance.slug}/registrations',
               json={'shift_id': shift.id, 'guest_name': 'Gast Meier'})
    assert rv.status_code == 201
    data = rv.get_json()['data']
    assert data['registered_by_admin'] is True

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.SHIFT_REGISTER).first()
    assert log is not None
    assert 'Admin-Eintragung' in log.details
    assert 'Gast Meier' == log.volunteer_name


def test_create_registration_with_volunteer_success(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance)
    rv = c.post(f'/api/admin/{instance.slug}/registrations',
               json={'shift_id': shift.id, 'volunteer_id': volunteer.id})
    assert rv.status_code == 201
    reg = _db.session.query(Registration).filter_by(shift_id=shift.id).first()
    assert reg.volunteer_id == volunteer.id
    assert reg.guest_name is None


def test_create_registration_duplicate_returns_409(client, admin_user, instance, volunteer):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance, max_volunteers=5)
    _db.session.add(Registration(shift_id=shift.id, volunteer_id=volunteer.id))
    _db.session.commit()

    rv = c.post(f'/api/admin/{instance.slug}/registrations',
               json={'shift_id': shift.id, 'volunteer_id': volunteer.id})
    assert rv.status_code == 409


# ---------------------------------------------------------------------------
# DELETE /registrations/<id>
# ---------------------------------------------------------------------------

def test_delete_registration_not_found_returns_404(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.delete(f'/api/admin/{instance.slug}/registrations/99999')
    assert rv.status_code == 404


def test_delete_registration_success_logs_details(client, admin_user, instance):
    c = _admin_client(client, admin_user)
    shift = _make_shift(instance, stand_name='Kasse')
    reg = Registration(shift_id=shift.id, guest_name='Zu Löschen')
    _db.session.add(reg)
    _db.session.commit()
    reg_id = reg.id

    rv = c.delete(f'/api/admin/{instance.slug}/registrations/{reg_id}')
    assert rv.status_code == 204
    assert _db.session.get(Registration, reg_id) is None

    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.SHIFT_UNREGISTER).first()
    assert log is not None
    assert 'Kasse' in log.details
    assert 'Admin-Abmeldung' in log.details
    assert log.volunteer_name == 'Zu Löschen'
