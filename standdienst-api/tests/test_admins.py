"""Regressionstests für app/api/admin/admins.py.

Beim Schreiben der Organizer-Coverage-Tests fiel auf, dass sowohl
admins.py als auch organizers.py validate_password_strength() ohne
role='admin'/'organizer' aufriefen und dadurch die laxe 8-Zeichen-
Volunteer-Regel statt der in CLAUDE.md vorgeschriebenen 12-Zeichen-
Komplexitätsregel für Admin/Organizer anwendeten. Für organizers.py siehe
test_organizers.py; hier nur die Regressionstests für admins.py – eine
vollständige funktionale Abdeckung von admins.py ist ein eigenes Modul.
"""
from unittest.mock import patch

from app.extensions import db as _db
from app.models import Admin
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


@patch('app.api.admin.admins.is_mail_configured', return_value=False)
def test_create_admin_weak_password_rejected(mock_mail, client, admin_user):
    """16 Zeichen, aber nur Kleinbuchstaben -> muss an der Admin-Komplexitätsregel scheitern."""
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/admins', json={
        'first_name': 'Neu', 'email': 'neuadmin@test.de', 'password': 'schwachaberlang',
    })
    assert rv.status_code == 400


@patch('app.api.admin.admins.is_mail_configured', return_value=False)
def test_create_admin_strong_password_accepted(mock_mail, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/admins', json={
        'first_name': 'Neu', 'email': 'neuadmin@test.de', 'password': 'SicheresPass1!',
    })
    assert rv.status_code == 201


@patch('app.api.admin.admins.send_mail')
@patch('app.api.admin.admins.is_mail_configured', return_value=True)
def test_create_admin_sends_invite_mail_when_configured(mock_configured, mock_send, client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/admins', json={
        'first_name': 'Neu', 'email': 'neuadmin2@test.de', 'password': 'SicheresPass1!',
    })
    assert rv.status_code == 201
    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == 'neuadmin2@test.de'


def test_update_admin_weak_password_rejected(client, admin_user):
    other = Admin(email='andereradmin@test.de', name='Anderer', first_name='Anderer')
    other.set_password('SicheresPass1!')
    _db.session.add(other)
    _db.session.commit()

    c = _admin_client(client, admin_user)
    rv = c.put(f'/api/admin/admins/{other.id}', json={'password': 'schwachaberlang'})
    assert rv.status_code == 400
