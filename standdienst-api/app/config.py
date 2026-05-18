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
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH_MB', 5)) * 1024 * 1024

    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_DEFAULT = '200 per hour'

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
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    LOG_LEVEL = 'WARNING'   # kein Info/Debug-Rauschen in der Testausgabe
