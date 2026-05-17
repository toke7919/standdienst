import os
import sqlite3
import pytest

os.environ.setdefault('SECRET_KEY', 'test-secret-key-32-bytes-minimum!!')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-key-32-bytes-minimum-ok!!')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('ADMIN_EMAIL', 'admin@test.de')
os.environ.setdefault('ADMIN_PASSWORD', 'TestPass1!')
os.environ.setdefault('FRONTEND_URL', 'http://localhost:5173')

from sqlalchemy import event
from sqlalchemy.engine import Engine
from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db
from app.models import Admin, Instance, SiteSettings, Volunteer


@event.listens_for(Engine, 'connect')
def _set_sqlite_fk(dbapi_connection, _):
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.execute('PRAGMA foreign_keys=ON')


@pytest.fixture(scope='session')
def app():
    application = create_app(TestingConfig)
    ctx = application.app_context()
    ctx.push()
    _db.create_all()
    yield application
    _db.drop_all()
    ctx.pop()


@pytest.fixture(scope='session')
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _clean_state(client):
    """DB-Tabellen und JWT-Cookies nach jedem Test leeren."""
    yield
    _db.session.rollback()
    for table in reversed(_db.metadata.sorted_tables):
        _db.session.execute(table.delete())
    _db.session.commit()
    # Werkzeug 3.x: cookie store ist _cookies dict
    client._cookies.clear()


@pytest.fixture
def admin_user():
    admin = Admin(email='testadmin@test.de', is_primary=True)
    admin.set_password('TestPass1!')
    _db.session.add(admin)
    _db.session.commit()
    return admin


@pytest.fixture
def instance():
    inst = Instance(slug='test-instanz', name='Testinstanz')
    _db.session.add(inst)
    _db.session.flush()
    settings = SiteSettings(instance_id=inst.id)
    _db.session.add(settings)
    _db.session.commit()
    return inst


@pytest.fixture
def volunteer(instance):
    v = Volunteer(
        instance_id=instance.id,
        name='Test Helfer',
        email='helfer@test.de',
    )
    v.set_password('TestPass1!')
    _db.session.add(v)
    _db.session.commit()
    return v


@pytest.fixture
def admin_token(client, admin_user):
    rv = client.post('/api/auth/login',
                     json={'email': admin_user.email, 'password': 'TestPass1!'})
    assert rv.status_code == 200
    return rv.get_json()


@pytest.fixture
def volunteer_token(client, volunteer, instance):
    rv = client.post('/api/auth/volunteer-login',
                     json={'slug': instance.slug,
                           'email': volunteer.email,
                           'password': 'TestPass1!'})
    assert rv.status_code == 200
    return rv.get_json()
