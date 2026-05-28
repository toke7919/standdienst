import pytest
from datetime import date, time


@pytest.fixture
def admin_client(client):
    """Eingeloggter Admin-Client."""
    from app.models import Admin, GlobalSettings
    from app.extensions import db as _db
    admin = Admin(email='dateadmin@test.de', is_primary=True)
    admin.set_password('TestPass1!')
    _db.session.add(admin)
    gs = GlobalSettings(setup_complete=True)
    _db.session.add(gs)
    _db.session.commit()
    rv = client.post('/api/auth/login', json={'email': 'dateadmin@test.de', 'password': 'TestPass1!'})
    assert rv.status_code == 200
    return client


@pytest.fixture
def date_setup(admin_client, instance):
    """Instanz mit einem EventDate + zwei Shifts."""
    from app.models import Stand, EventDate, Shift
    from app.extensions import db as _db
    stand = Stand(instance_id=instance.id, name='Hauptstand')
    _db.session.add(stand)
    _db.session.flush()
    ev = EventDate(instance_id=instance.id, date=date(2026, 8, 1), label='Tag 1', is_draft=False)
    _db.session.add(ev)
    _db.session.flush()
    s1 = Shift(stand_id=stand.id, event_date_id=ev.id,
               start_time=time(9, 0), end_time=time(12, 0), max_volunteers=3)
    s2 = Shift(stand_id=stand.id, event_date_id=ev.id,
               start_time=time(13, 0), end_time=time(17, 0), max_volunteers=2)
    _db.session.add_all([s1, s2])
    _db.session.commit()
    return {'instance': instance, 'event_date': ev, 'stand': stand, 'shifts': [s1, s2]}


def test_duplicate_date_creates_new_draft(admin_client, date_setup):
    """Duplikat-Endpunkt erstellt neues EventDate als Entwurf mit kopierten Shifts."""
    ev = date_setup['event_date']
    instance = date_setup['instance']

    rv = admin_client.post(
        f'/api/admin/{instance.slug}/dates/{ev.id}/duplicate',
        json={'date': '2026-08-15'},
    )
    assert rv.status_code == 201, rv.get_json()
    data = rv.get_json()['data']
    assert data['date'] == '2026-08-15'
    assert data['label'] == 'Tag 1'
    assert data['is_draft'] is True

    # Shifts wurden kopiert
    from app.models import EventDate, Shift
    from app.extensions import db as _db
    from sqlalchemy import select
    new_ev = _db.session.scalars(select(EventDate).filter_by(id=data['id'])).first()
    assert new_ev is not None
    new_shifts = list(new_ev.shifts)
    assert len(new_shifts) == 2
    times = {(s.start_time, s.end_time) for s in new_shifts}
    from datetime import time
    assert (time(9, 0), time(12, 0)) in times
    assert (time(13, 0), time(17, 0)) in times


def test_duplicate_date_conflict(admin_client, date_setup):
    """Duplikat auf bereits bestehendes Datum gibt 409."""
    ev = date_setup['event_date']
    instance = date_setup['instance']

    rv = admin_client.post(
        f'/api/admin/{instance.slug}/dates/{ev.id}/duplicate',
        json={'date': '2026-08-01'},  # Gleiches Datum wie Source
    )
    assert rv.status_code == 409


def test_duplicate_date_missing_date(admin_client, date_setup):
    """Duplikat ohne Zieldatum gibt 422."""
    ev = date_setup['event_date']
    instance = date_setup['instance']

    rv = admin_client.post(
        f'/api/admin/{instance.slug}/dates/{ev.id}/duplicate',
        json={},
    )
    assert rv.status_code == 422
