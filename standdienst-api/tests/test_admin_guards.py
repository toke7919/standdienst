"""Tests für Admin-Sicherheitsguards."""
from app.extensions import db as _db
from app.models import Admin


def _create_and_login(client, email, is_primary=False):
    admin = Admin(email=email, is_primary=is_primary)
    admin.set_password('TestPass1!')
    _db.session.add(admin)
    _db.session.commit()
    rv = client.post('/api/auth/login', json={'email': email, 'password': 'TestPass1!'})
    assert rv.status_code == 200
    return admin


def test_set_is_primary_true_demotes_old_primary(client):
    """Wenn ein Admin auf is_primary=True gesetzt wird, wird der alte Primary abgewählt."""
    old_primary = _create_and_login(client, 'primary@test.de', is_primary=True)
    new_admin = Admin(email='new@test.de', is_primary=False)
    new_admin.set_password('TestPass1!')
    _db.session.add(new_admin)
    _db.session.commit()

    old_id = old_primary.id
    new_id = new_admin.id

    rv = client.put(f'/api/admin/admins/{new_id}',
                    json={'is_primary': True})
    assert rv.status_code == 200

    # Remove the scoped session so the next query opens a fresh connection/transaction,
    # bypassing any identity-map or transaction-level read caching.
    _db.session.remove()
    old_reloaded = Admin.query.filter_by(id=old_id).first()
    new_reloaded = Admin.query.filter_by(id=new_id).first()
    assert new_reloaded.is_primary is True
    assert old_reloaded.is_primary is False, "Alter Primary muss abgewählt werden"


def test_cannot_demote_only_primary(client):
    """Der letzte Primary kann nicht auf is_primary=False gesetzt werden."""
    primary = _create_and_login(client, 'primary2@test.de', is_primary=True)

    rv = client.put(f'/api/admin/admins/{primary.id}',
                    json={'is_primary': False})
    assert rv.status_code == 400
