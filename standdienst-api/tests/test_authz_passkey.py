"""Autorisierungstests für app/api/passkey.py.

Alle Routen: @jwt_required() ohne require_staff/require_admin, dafür
inline geprüft (role in ('admin', 'organizer')) bzw. implizit über
_load_user(), das für andere Rollen None liefert. Wichtigster Fall:
Besitzer-Isolation bei delete_credential – ein Admin/Organizer darf nur
seine EIGENEN Passkeys löschen, nicht die eines anderen Kontos.
"""
from app.extensions import db as _db
from app.models.passkey import PasskeyCredential
from tests.conftest import assign_organizer as _assign, login as _login


def _make_passkey(admin_id=None, organizer_id=None, credential_id='cred-1'):
    pk = PasskeyCredential(
        admin_id=admin_id, organizer_id=organizer_id,
        credential_id=credential_id, public_key='dummy-key',
    )
    _db.session.add(pk)
    _db.session.commit()
    return pk


def test_register_begin_unauthenticated_rejected(client):
    rv = client.post('/api/auth/passkey/register/begin')
    assert rv.status_code == 401


def test_volunteer_cannot_start_passkey_registration(client, instance, volunteer_token):
    rv = client.post('/api/auth/passkey/register/begin')
    assert rv.status_code == 403


def test_volunteer_cannot_list_credentials(client, instance, volunteer_token):
    rv = client.get('/api/auth/passkey/credentials')
    # _load_user() kennt die Rolle 'volunteer' nicht -> None -> 404, nicht 403
    assert rv.status_code == 404


def test_admin_can_list_own_credentials(client, admin_user):
    _make_passkey(admin_id=admin_user.id)
    _login(client, admin_user.email)
    rv = client.get('/api/auth/passkey/credentials')
    assert rv.status_code == 200
    assert len(rv.get_json()['credentials']) == 1


def test_admin_cannot_delete_other_admins_passkey(client, admin_user):
    from app.models import Admin
    other = Admin(email='other-admin@test.de', is_primary=False)
    other.set_password('TestPass1!')
    _db.session.add(other)
    _db.session.commit()
    foreign_pk = _make_passkey(admin_id=other.id)

    _login(client, admin_user.email)
    rv = client.delete(f'/api/auth/passkey/credentials/{foreign_pk.id}')
    assert rv.status_code == 403


def test_organizer_cannot_delete_admins_passkey(client, instance, organizer_user, admin_user):
    foreign_pk = _make_passkey(admin_id=admin_user.id)
    _assign(organizer_user, instance)
    _login(client, organizer_user.email)
    rv = client.delete(f'/api/auth/passkey/credentials/{foreign_pk.id}')
    assert rv.status_code == 403


def test_admin_can_delete_own_passkey(client, admin_user):
    own_pk = _make_passkey(admin_id=admin_user.id)
    _login(client, admin_user.email)
    rv = client.delete(f'/api/auth/passkey/credentials/{own_pk.id}')
    assert rv.status_code == 200
