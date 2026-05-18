"""Zentrales Logging-Setup für Standdienst.

Konfiguriert den 'app'-Logger-Baum mit:
  - Console-Handler (immer aktiv)
  - logs/app.log   – alle Level ab LOG_LEVEL, rotierend (10 MB × 5)
  - logs/error.log – nur WARNING und höher, rotierend (5 MB × 5)

Jede Log-Zeile enthält eine eindeutige Request-ID, damit alle Zeilen
eines Requests im Fehlerfall per grep zusammengeführt werden können:

  2026-05-17 14:23:01 [ERROR   ] app.api.public:87 [a3f2c91d] Unbekannter Fehler

Verwendung in jedem Modul:
  import logging
  log = logging.getLogger(__name__)

  log.debug('...')
  log.info('...')
  log.warning('...')
  log.error('...')
  log.exception('...')  # wie error(), hängt aber Traceback an
"""
import logging
import logging.handlers
import os

_LOG_FORMAT = (
    '%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d [%(request_id)s] %(message)s'
)
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

_APP_LOG_MAX_BYTES = 10 * 1024 * 1024   # 10 MB
_ERR_LOG_MAX_BYTES = 5 * 1024 * 1024    # 5 MB
_LOG_BACKUP_COUNT = 5


class _RequestIdFilter(logging.Filter):
    """Fügt request_id aus Flask g in jeden LogRecord ein.

    Außerhalb eines Request-Kontexts (z.B. APScheduler-Jobs) wird '-' gesetzt.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from flask import g, has_request_context
            record.request_id = g.request_id if has_request_context() else '-'
        except Exception:
            record.request_id = '-'
        return True


def init_logging(app) -> None:
    """Logging initialisieren – einmalig aus create_app() aufrufen."""
    log_level_name: str = app.config.get('LOG_LEVEL', 'INFO').upper()
    log_level: int = getattr(logging, log_level_name, logging.INFO)
    log_dir: str = app.config.get('LOG_DIR', 'logs')
    testing: bool = bool(app.config.get('TESTING'))

    req_filter = _RequestIdFilter()
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Eltern-Logger für alle app.* Module (propagate=False → kein Root-Konflikt)
    logger = logging.getLogger('app')

    # Schutz vor doppelter Initialisierung (z.B. mehrere Test-Fixtures)
    if logger.handlers:
        return

    logger.setLevel(log_level)
    logger.propagate = False

    # ── Console ──────────────────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(req_filter)
    logger.addHandler(console_handler)

    # ── Datei-Handler (nur außerhalb von Tests) ───────────────────────────────
    if not testing:
        os.makedirs(log_dir, exist_ok=True)

        # app.log – alle Level ab Konfiguration
        app_fh = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=_APP_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding='utf-8',
        )
        app_fh.setLevel(log_level)
        app_fh.setFormatter(formatter)
        app_fh.addFilter(req_filter)
        logger.addHandler(app_fh)

        # error.log – nur WARNING und höher (inkl. Tracebacks von log.exception)
        err_fh = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'error.log'),
            maxBytes=_ERR_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding='utf-8',
        )
        err_fh.setLevel(logging.WARNING)
        err_fh.setFormatter(formatter)
        err_fh.addFilter(req_filter)
        logger.addHandler(err_fh)

    # ── Dritthersteller-Logger auf WARNING begrenzen ──────────────────────────
    for noisy in ('apscheduler', 'sqlalchemy.engine', 'werkzeug'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger.info(
        'Logging initialisiert (level=%s, dir=%s)',
        log_level_name,
        log_dir if not testing else 'deaktiviert (Testing)',
    )


def get_logger(name: str) -> logging.Logger:
    """Gibt einen benannten Logger zurück – Kurzform für logging.getLogger(name)."""
    return logging.getLogger(name)
