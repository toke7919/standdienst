def test_login_admin_success(client, admin_user):
    rv = client.post('/api/auth/login',
                     json={'email': admin_user.email, 'password': 'TestPass1!'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'user' in data
    assert data['user']['role'] == 'admin'


def test_login_admin_wrong_password(client, admin_user):
    rv = client.post('/api/auth/login',
                     json={'email': admin_user.email, 'password': 'falsch'})
    assert rv.status_code == 401


def test_login_admin_unknown_email(client):
    rv = client.post('/api/auth/login',
                     json={'email': 'nobody@test.de', 'password': 'TestPass1!'})
    assert rv.status_code == 401


def test_login_volunteer_success(client, volunteer, instance):
    rv = client.post('/api/auth/volunteer-login',
                     json={'slug': instance.slug,
                           'email': volunteer.email,
                           'password': 'TestPass1!'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['user']['role'] == 'volunteer'


def test_login_volunteer_wrong_instance(client, volunteer):
    rv = client.post('/api/auth/volunteer-login',
                     json={'slug': 'nicht-vorhanden',
                           'email': volunteer.email,
                           'password': 'TestPass1!'})
    assert rv.status_code == 404


def test_me_requires_auth(client):
    rv = client.get('/api/auth/me')
    # Ohne Token: 401 (via jwt.unauthorized_loader)
    assert rv.status_code == 401
    assert 'error' in rv.get_json()


def test_logout(client, admin_user):
    client.post('/api/auth/login',
                json={'email': admin_user.email, 'password': 'TestPass1!'})
    rv = client.post('/api/auth/logout')
    assert rv.status_code == 200


def test_forgot_password_always_200(client, admin_user):
    rv = client.post('/api/auth/forgot-password',
                     json={'email': admin_user.email, 'type': 'admin'})
    assert rv.status_code == 200


def test_reset_password_weak(client):
    rv = client.post('/api/auth/reset-password',
                     json={'token': 'fake', 'password': 'kurz', 'type': 'admin'})
    assert rv.status_code == 400


def test_reset_password_admin_requires_uppercase(client):
    """Admin-Passwort mit 12 Zeichen aber ohne Großbuchstabe → abgelehnt."""
    rv = client.post('/api/auth/reset-password',
                     json={'token': 'fake', 'password': 'aaaa1111!!!!', 'type': 'admin'})
    assert rv.status_code == 400


def test_reset_password_admin_requires_digit(client):
    """Admin-Passwort ohne Ziffer → abgelehnt."""
    rv = client.post('/api/auth/reset-password',
                     json={'token': 'fake', 'password': 'AAAAbbbb!!!!', 'type': 'admin'})
    assert rv.status_code == 400


def test_reset_password_admin_requires_special_char(client):
    """Admin-Passwort ohne Sonderzeichen → abgelehnt."""
    rv = client.post('/api/auth/reset-password',
                     json={'token': 'fake', 'password': 'AAAAbbbb1234', 'type': 'admin'})
    assert rv.status_code == 400


def test_reset_password_organizer_requires_complexity(client):
    """Organizer-Passwort unterliegt denselben Regeln wie Admin."""
    rv = client.post('/api/auth/reset-password',
                     json={'token': 'fake', 'password': 'kurz', 'type': 'organizer'})
    assert rv.status_code == 400
