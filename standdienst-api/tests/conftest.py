import os
import sqlite3
from unittest.mock import patch
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
from app.models import Admin, Instance, Organizer, SiteSettings, Volunteer, organizer_instances


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
    """DB-Tabellen, JWT-Cookies und Settings-Cache nach jedem Test leeren."""
    yield
    _db.session.rollback()
    for table in reversed(_db.metadata.sorted_tables):
        _db.session.execute(table.delete())
    _db.session.commit()
    _db.session.expunge_all()
    # Werkzeug 3.x: cookie store ist _cookies dict
    client._cookies.clear()
    # Settings-Cache leeren, damit gecachte Werte keine Tests beeinflussen
    from app.utils.settings_cache import _cache
    _cache.clear()


@pytest.fixture(autouse=True)
def _no_real_git_repo_fallback():
    """Sicherheitsnetz: app.api.admin.update._repo_slug_and_pat() fällt ohne
    konfiguriertes GlobalSettings.github_repo auf den ECHTEN `git remote` dieses
    Checkouts zurück (toke7919/standdienst). Ein Test, der das vergisst zu mocken,
    würde sonst reale GitHub-Calls, einen echten Tarball-Download/-Copytree, echtes
    pip install/npm run build und echte systemctl-Restarts auslösen – ist bereits
    passiert und hat die Dev-Maschine per Swap-Erschöpfung lahmgelegt. Tests, die
    den echten Fallback bewusst prüfen wollen, patchen ihn lokal erneut."""
    with patch('app.api.admin.update._git_repo_slug', return_value=None):
        yield


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
def other_instance():
    """Zweite Instanz für Cross-Instanz-Zugriffstests (Fremdzugriff darf nicht durchkommen)."""
    inst = Instance(slug='andere-instanz', name='Andere Instanz')
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
def organizer_user():
    org = Organizer(name='Org Tester', email='org@test.de', is_instance_admin=False)
    org.set_password('TestPass1!')
    _db.session.add(org)
    _db.session.commit()
    return org


@pytest.fixture
def instance_admin_user():
    org = Organizer(name='InstAdmin Tester', email='instadmin@test.de', is_instance_admin=True)
    org.set_password('TestPass1!')
    _db.session.add(org)
    _db.session.commit()
    return org


def assign_organizer(organizer, instance, is_instance_admin=None):
    """Weist einen Organizer/Instanz-Admin einer Instanz zu (organizer_instances-Zuordnungstabelle)."""
    admin_flag = organizer.is_instance_admin if is_instance_admin is None else is_instance_admin
    _db.session.execute(organizer_instances.insert().values(
        organizer_id=organizer.id, instance_id=instance.id,
        is_primary=False, is_instance_admin=admin_flag,
    ))
    _db.session.commit()


def login(client, email, password='TestPass1!'):
    rv = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert rv.status_code == 200
    return rv


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
