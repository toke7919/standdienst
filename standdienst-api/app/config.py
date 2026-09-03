import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f'Env-Variable {key!r} ist nicht gesetzt')
    return value


class Config:
    SECRET_KEY = _require('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = _require('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', _require('SECRET_KEY'))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SAMESITE = 'Strict'
    JWT_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_COOKIE_NAME = 'access_token'
    JWT_REFRESH_COOKIE_NAME = 'refresh_token'
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    WEBAUTHN_ORIGIN = os.getenv('WEBAUTHN_ORIGIN', '')
    WEBAUTHN_RP_ID = os.getenv('WEBAUTHN_RP_ID', '')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    BACKUP_DIR = os.getenv('BACKUP_DIR', 'backups')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH_MB', 5)) * 1024 * 1024

    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_DEFAULT = '600 per hour'

    MAIL_SERVER = os.getenv('MAIL_SERVER', '')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', '')

    FAIL2BAN_LOG = os.getenv('FAIL2BAN_LOG', 'logs/auth.log')

    # Logging
    _debug_mode = os.getenv('FLASK_DEBUG', '0') not in ('0', 'false', 'False', '')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG' if _debug_mode else 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', 'logs')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # Config.SQLALCHEMY_ENGINE_OPTIONS setzt pool_recycle=300 (für Postgres in
    # Produktion gedacht, damit der DB-Server keine alten Connections killt).
    # Für sqlite:///:memory: ist das aktiv schädlich: SQLAlchemy verwirft die
    # Connection nach 300s und öffnet eine neue – bei einer In-Memory-DB
    # bedeutet das eine komplett leere Datenbank mitten im Testlauf ("no such
    # table"). Mit wachsender Testsuite dauert ein Coverage-Lauf inzwischen
    # >300s, wodurch das real reproduzierbar wurde (CI-Läufe nach #192/#195).
    SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    LOG_LEVEL = 'WARNING'   # kein Info/Debug-Rauschen in der Testausgabe
    # Dummy-SMTP damit is_mail_configured()=True; send_mail() schlägt fehl, aber Tests fangen das ab
    MAIL_SERVER = 'localhost'
    ALTCHA_MAX_NUMBER = 100  # schnelle Brute-Force-Lösung in Tests
