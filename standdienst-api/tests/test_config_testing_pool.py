"""Regressionstest: TestingConfig darf keinen pool_recycle für sqlite:///:memory: setzen.

Config.SQLALCHEMY_ENGINE_OPTIONS setzt pool_recycle=300 (für Postgres in
Produktion gedacht). Für eine In-Memory-SQLite-DB ist das aktiv schädlich:
SQLAlchemy verwirft die Connection nach 300s und öffnet eine neue - bei
sqlite:///:memory: bedeutet eine neue Connection eine komplett leere
Datenbank, mitten im Testlauf ("no such table: admins"). Mit wachsender
Testsuite dauert ein Coverage-Lauf inzwischen >300s, wodurch das real in CI
reproduzierbar wurde.
"""
from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db


def test_testing_config_has_no_pool_recycle(app):
    assert app.config['SQLALCHEMY_ENGINE_OPTIONS'].get('pool_recycle') is None


def test_testing_engine_pool_recycle_disabled(app):
    """-1 bedeutet: SQLAlchemy verwirft Connections nie altersbasiert."""
    assert _db.engine.pool._recycle == -1
