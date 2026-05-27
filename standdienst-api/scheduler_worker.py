"""Standalone-Einstiegspunkt für den APScheduler-Prozess.

Wird als separater systemd-Dienst (standdienst-scheduler.service) gestartet
und läuft unabhängig von Gunicorn, sodass Jobs exakt einmal ausgeführt werden.
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s – %(message)s',
    stream=sys.stdout,
)

from app import create_app
from app.utils.scheduler import run_scheduler

app = create_app()
run_scheduler(app)
