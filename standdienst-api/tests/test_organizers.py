"""Funktionale Tests für app/api/admin/organizers.py.

Autorisierung (@require_admin, nur Global-Admin) ist bereits in
test_authz_organizers.py abgedeckt. Hier geht es um Statuscode, Response-Form
und Geschäftslogik: Validierung, Duplikat-Prüfung, Passwort-Stärke,
Instanz-Zuweisung inkl. is_instance_admin-Flag, Einladungsmail (gemockt) und
deren Fehlerresilienz.

organizers.py importiert is_mail_configured/send_mail auf Modulebene (nicht wie
export.py lokal pro Funktion) -> gemockt wird daher auf
app.api.admin.organizers.is_mail_configured/send_mail, nicht auf app.utils.mail.
"""
from unittest.mock import patch

from app.extensions import db as _db
from app.models import Organizer, ActivityLog
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


# ---------------------------------------------------------------------------
# GET /organizers – Liste
# ---------------------------------------------------------------------------

def test_list_organizers_empty(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/organizers')
    assert rv.status_code == 200
    body = rv.get_json()
    assert body['data'] == []
    assert body['total'] == 0


def test_list_organizers_returns_created_ones_sorted_by_name(client, admin_user):
    c = _admin_client(client, admin_user)
    for name in ('Zora', 'Anna'):
        org = Organizer(email=f'{name.lower()}@test.de', name=name, first_name=name)
        _db.session.add(org)
    _db.session.commit()

    rv = c.get('/api/admin/organizers')
    names = [o['name'] for o in rv.get_json()['data']]
    assert names == ['Anna', 'Zora']


# ---------------------------------------------------------------------------
# POST /organizers – Anlegen
# ---------------------------------------------------------------------------

def test_create_organizer_validation_error_missing_fields(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/organizers', json={})
    assert rv.status_code == 422


def test_create_organizer_duplicate_email_rejected(client, admin_user):
    c = _admin_client(client, admin_user)
    org = Organizer(email='dup@test.de', name='Bestehend', first_name='Bestehend')
    _db.session.add(org)
    _db.session.commit()

    rv = c.post('/api/admin/organizers', json={'first_name': 'Neu', 'email': 'dup@test.de'})
    assert rv.status_code == 409


@patch('app.api.admin.organizers.is_mail_configured', return_value=False)
def test_create_organizer_without_password_has_no_login(mock_mail, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/organizers', json={'first_name': 'Neu', 'last_name': 'Org', 'email': 'neu@test.de'})
    assert rv.status_code == 201
    data = rv.get_json()['data']
    assert data['has_login'] is False
    assert data['name'] == 'Neu Org'


@patch('app.api.admin.organizers.is_mail_configured', return_value=False)
def test_create_organizer_weak_password_rejected(mock_mail, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/organizers', json={'first_name': 'Neu', 'email': 'neu@test.de', 'password': 'schwachaberlang'})
    assert rv.status_code == 400


@patch('app.api.admin.organizers.is_mail_configured', return_value=False)
def test_create_organizer_empty_password_string_treated_as_no_password(mock_mail, client, admin_user):
    """Leerer String (z.B. vom Frontend-Formular) darf nicht als 'zu schwach' abgelehnt werden."""
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/organizers', json={'first_name': 'Neu', 'email': 'neu@test.de', 'password': ''})
    assert rv.status_code == 201
    assert rv.get_json()['data']['has_login'] is False


@patch('app.api.admin.organizers.is_mail_configured', return_value=False)
def test_create_organizer_with_valid_password_has_login(mock_mail, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/organizers', json={
        'first_name': 'Neu', 'email': 'neu@test.de', 'password': 'SicheresPass1!',
    })
    assert rv.status_code == 201
    assert rv.get_json()['data']['has_login'] is True


@patch('app.api.admin.organizers.is_mail_configured', return_value=False)
def test_create_organizer_with_instance_admin_ids_sets_is_instance_admin(mock_mail, client, admin_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/organizers', json={
        'first_name': 'Neu', 'email': 'neu@test.de',
        'instance_ids': [instance.id], 'instance_admin_ids': [instance.id],
    })
    assert rv.status_code == 201
    data = rv.get_json()['data']
    assert data['is_instance_admin'] is True
    assert data['instance_ids'] == [instance.id]
    assert data['instance_admin_ids'] == [instance.id]


@patch('app.api.admin.organizers.is_mail_configured', return_value=False)
def test_create_organizer_activity_log_written(mock_mail, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/organizers', json={'first_name': 'Neu', 'email': 'neu@test.de'})
    assert rv.status_code == 201
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_ORGANIZER).first()
    assert log is not None
    assert 'neu@test.de' in log.details


@patch('app.api.admin.organizers.send_mail')
@patch('app.api.admin.organizers.is_mail_configured', return_value=True)
def test_create_organizer_sends_invite_mail_when_configured(mock_configured, mock_send, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/organizers', json={'first_name': 'Neu', 'email': 'neu@test.de'})
    assert rv.status_code == 201
    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == 'neu@test.de'


@patch('app.api.admin.organizers.send_mail', side_effect=RuntimeError('SMTP down'))
@patch('app.api.admin.organizers.is_mail_configured', return_value=True)
def test_create_organizer_still_succeeds_when_invite_mail_fails(mock_configured, mock_send, client, admin_user):
    """Mail-Versand-Fehler darf die Organisator-Anlage nicht verhindern (nur geloggt)."""
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/organizers', json={'first_name': 'Neu', 'email': 'neu@test.de'})
    assert rv.status_code == 201


# ---------------------------------------------------------------------------
# GET /organizers/<id>
# ---------------------------------------------------------------------------

def test_get_organizer_not_found(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/organizers/99999')
    assert rv.status_code == 404


def test_get_organizer_returns_data(client, admin_user, organizer_user):
    c = _admin_client(client, admin_user)
    rv = c.get(f'/api/admin/organizers/{organizer_user.id}')
    assert rv.status_code == 200
    assert rv.get_json()['data']['email'] == organizer_user.email


# ---------------------------------------------------------------------------
# PUT /organizers/<id>
# ---------------------------------------------------------------------------

def test_update_organizer_not_found(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.put('/api/admin/organizers/99999', json={'first_name': 'X'})
    assert rv.status_code == 404


def test_update_organizer_validation_error(client, admin_user, organizer_user):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/organizers/{organizer_user.id}', json={'email': 'keine-email'})
    assert rv.status_code == 422


def test_update_organizer_duplicate_email_rejected(client, admin_user, organizer_user):
    other = Organizer(email='andere@test.de', name='Andere', first_name='Andere')
    _db.session.add(other)
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/organizers/{organizer_user.id}', json={'email': 'andere@test.de'})
    assert rv.status_code == 409


def test_update_organizer_own_email_unchanged_allowed(client, admin_user, organizer_user):
    """Die eigene E-Mail erneut zu senden darf nicht als Duplikat gelten."""
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/organizers/{organizer_user.id}', json={'email': organizer_user.email})
    assert rv.status_code == 200


def test_update_organizer_names_and_password(client, admin_user, organizer_user):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/organizers/{organizer_user.id}', json={
        'first_name': 'Neuer', 'last_name': 'Name', 'password': 'NochSicherer1!',
    })
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['name'] == 'Neuer Name'
    assert data['has_login'] is True


def test_update_organizer_empty_password_string_keeps_existing_password(client, admin_user, organizer_user):
    """Leerer String beim Update darf das bestehende Passwort nicht anfassen/ablehnen."""
    old_hash = organizer_user.password_hash
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/organizers/{organizer_user.id}', json={'password': ''})
    assert rv.status_code == 200
    assert organizer_user.password_hash == old_hash


def test_update_organizer_weak_password_rejected(client, admin_user, organizer_user):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/organizers/{organizer_user.id}', json={'password': 'schwachaberlang'})
    assert rv.status_code == 400


def test_update_organizer_instance_assignment_updates_is_instance_admin(client, admin_user, organizer_user, instance):
    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/organizers/{organizer_user.id}', json={
        'instance_ids': [instance.id], 'instance_admin_ids': [instance.id],
    })
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['is_instance_admin'] is True
    assert data['instance_ids'] == [instance.id]


def test_update_organizer_reassignment_removes_previous_instance(client, admin_user, organizer_user, instance, other_instance):
    from tests.conftest import assign_organizer
    assign_organizer(organizer_user, instance, is_instance_admin=True)

    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/organizers/{organizer_user.id}', json={'instance_ids': [other_instance.id]})
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['instance_ids'] == [other_instance.id]


def test_update_organizer_activity_log_written(client, admin_user, organizer_user):
    c = _admin_client(client, admin_user)
    c.put(f'/api/admin/organizers/{organizer_user.id}', json={'first_name': 'Geändert'})
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_ORGANIZER).first()
    assert log is not None
    assert 'geändert' in log.details.lower()


# ---------------------------------------------------------------------------
# DELETE /organizers/<id>
# ---------------------------------------------------------------------------

def test_delete_organizer_not_found(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.delete('/api/admin/organizers/99999')
    assert rv.status_code == 404


def test_delete_organizer_removes_record(client, admin_user, organizer_user):
    org_id = organizer_user.id
    c = _admin_client(client, admin_user)
    rv = c.delete(f'/api/admin/organizers/{org_id}')
    assert rv.status_code == 204
    assert _db.session.get(Organizer, org_id) is None


def test_delete_organizer_activity_log_written(client, admin_user, organizer_user):
    email = organizer_user.email
    c = _admin_client(client, admin_user)
    c.delete(f'/api/admin/organizers/{organizer_user.id}')
    log = _db.session.query(ActivityLog).filter_by(event_type=ActivityLog.AUDIT_ORGANIZER).first()
    assert log is not None
    assert email in log.details


# ---------------------------------------------------------------------------
# POST /organizers/<id>/resend-invite
# ---------------------------------------------------------------------------

def test_resend_invite_not_found(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/organizers/99999/resend-invite')
    assert rv.status_code == 404


def test_resend_invite_already_active_rejected(client, admin_user, organizer_user):
    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/organizers/{organizer_user.id}/resend-invite')
    assert rv.status_code == 400


@patch('app.api.admin.organizers.is_mail_configured', return_value=False)
def test_resend_invite_mail_not_configured_returns_503(mock_mail, client, admin_user):
    org = Organizer(email='inaktiv@test.de', name='Inaktiv', first_name='Inaktiv')
    _db.session.add(org)
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/organizers/{org.id}/resend-invite')
    assert rv.status_code == 503


@patch('app.api.admin.organizers.send_mail')
@patch('app.api.admin.organizers.is_mail_configured', return_value=True)
def test_resend_invite_success(mock_configured, mock_send, client, admin_user):
    org = Organizer(email='inaktiv@test.de', name='Inaktiv', first_name='Inaktiv')
    _db.session.add(org)
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/organizers/{org.id}/resend-invite')
    assert rv.status_code == 200
    mock_send.assert_called_once()


@patch('app.api.admin.organizers.send_mail', side_effect=RuntimeError('SMTP down'))
@patch('app.api.admin.organizers.is_mail_configured', return_value=True)
def test_resend_invite_mail_failure_returns_500(mock_configured, mock_send, client, admin_user):
    org = Organizer(email='inaktiv@test.de', name='Inaktiv', first_name='Inaktiv')
    _db.session.add(org)
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.post(f'/api/admin/organizers/{org.id}/resend-invite')
    assert rv.status_code == 500
