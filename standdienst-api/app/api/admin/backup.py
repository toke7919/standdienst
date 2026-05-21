import base64
import hashlib
import hmac as _hmac
import io
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g, request, send_file
from werkzeug.utils import secure_filename
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text

from . import admin_bp
from ...extensions import db
from ...utils.auth import require_admin
from ...utils.responses import ok, error

MAX_BACKUPS = 20


def _backup_dir() -> Path:
    d = Path(current_app.config.get('BACKUP_DIR', 'backups'))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _derive_aes_key() -> bytes:
    secret = current_app.config['SECRET_KEY']
    return hashlib.sha256(secret.encode()).digest()


def _encrypt(data: bytes, key: bytes) -> bytes:
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aesgcm.encrypt(nonce, data, None)


def _decrypt(data: bytes, key: bytes) -> bytes:
    aesgcm = AESGCM(key)
    nonce, ciphertext = data[:12], data[12:]
    return aesgcm.decrypt(nonce, ciphertext, None)


def _dump_database() -> bytes:
    buf = io.StringIO()
    buf.write(f'-- Standdienst Backup {datetime.now(timezone.utc).isoformat()}\n')
    with db.engine.connect() as conn:
        for table in db.metadata.sorted_tables:
            rows = conn.execute(table.select()).fetchall()
            if not rows:
                continue
            cols = ', '.join(f'"{c}"' for c in table.columns.keys())
            for row in rows:
                vals = ', '.join(_sql_value(v) for v in row)
                buf.write(f'INSERT INTO "{table.name}" ({cols}) VALUES ({vals});\n')
    return buf.getvalue().encode('utf-8')


def _sql_value(v) -> str:
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'TRUE' if v else 'FALSE'
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def _list_backups(backup_dir: Path) -> list[dict]:
    files = sorted(
        list(backup_dir.glob('*.enc')) + list(backup_dir.glob('*.sql.gz')),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [
        {
            'filename': f.name,
            'size_bytes': f.stat().st_size,
            'created_at': datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
            'type': 'encrypted' if f.suffix == '.enc' else 'sql_gz',
        }
        for f in files
    ]


def _autorotate(backup_dir: Path) -> None:
    files = sorted(backup_dir.glob('*.enc'), key=lambda f: f.stat().st_mtime)
    while len(files) >= MAX_BACKUPS:
        files[0].unlink()
        files = files[1:]


def _restore_from_bytes(sql_bytes: bytes) -> None:
    stmts = [
        line.strip()
        for line in sql_bytes.decode('utf-8').split('\n')
        if line.strip() and not line.startswith('--')
    ]
    with db.engine.begin() as conn:
        try:
            conn.execute(text("SET session_replication_role = 'replica'"))
        except Exception:
            pass  # SQLite kennt dieses Kommando nicht
        for table in reversed(db.metadata.sorted_tables):
            conn.execute(table.delete())
        for stmt in stmts:
            conn.execute(text(stmt))
        try:
            conn.execute(text("SET session_replication_role = 'origin'"))
        except Exception:
            pass


# Magisches Prefix zur Erkennung HMAC-signierter Backups
_HMAC_MAGIC = b'SDHMAC'
_HMAC_LEN = 32  # SHA-256


def _sign_payload(sql_bytes: bytes, key: bytes) -> bytes:
    """Hängt HMAC-SHA-256-Signatur mit Magic-Prefix vor die Nutzdaten."""
    sig = _hmac.new(key, sql_bytes, hashlib.sha256).digest()
    return _HMAC_MAGIC + sig + sql_bytes


def _verify_payload(data: bytes, key: bytes) -> bytes:
    """Gibt SQL-Bytes zurück. Wirft ValueError bei ungültiger Signatur."""
    if not data.startswith(_HMAC_MAGIC):
        # Altes Backup ohne Signatur – akzeptieren, Warnung im Log
        current_app.logger.warning('Backup ohne HMAC-Signatur wird wiederhergestellt (altes Format)')
        return data
    offset = len(_HMAC_MAGIC)
    sig_stored = data[offset:offset + _HMAC_LEN]
    sql_bytes = data[offset + _HMAC_LEN:]
    sig_expected = _hmac.new(key, sql_bytes, hashlib.sha256).digest()
    if not _hmac.compare_digest(sig_stored, sig_expected):
        raise ValueError('Backup-Signatur ungültig')
    return sql_bytes


def _validate_filename(name: str) -> bool:
    if not name or '/' in name or name.startswith('.'):
        return False
    return name.endswith('.enc') or name.endswith('.sql.gz')


def run_backup(label: str | None = None) -> str:
    """Erstellt ein Backup und gibt den Dateinamen zurück. Wirft Exception bei Fehler."""
    d = _backup_dir()
    _autorotate(d)
    key = _derive_aes_key()
    raw = _dump_database()
    signed = _sign_payload(raw, key)
    encrypted = _encrypt(signed, key)
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    suffix = f'_{label}' if label else ''
    name = f'standdienst_{ts}{suffix}.enc'
    (d / name).write_bytes(encrypted)
    current_app.logger.info('Backup erstellt: %s (%d Bytes)', name, len(encrypted))
    return name


@admin_bp.route('/backup/list', methods=['GET'])
@require_admin
def list_backups():
    return ok({'backups': _list_backups(_backup_dir())})


@admin_bp.route('/backup/create', methods=['POST'])
@require_admin
def create_backup():
    try:
        name = run_backup()
        return ok({'backups': _list_backups(_backup_dir()), 'created': name}, 'Backup erstellt')
    except Exception as e:
        current_app.logger.exception('Backup fehlgeschlagen')
        return error(f'Backup fehlgeschlagen: {e}', 500)


@admin_bp.route('/backup/<name>', methods=['DELETE'])
@require_admin
def delete_backup(name):
    if not _validate_filename(name):
        return error('Ungültiger Dateiname', 400)
    f = _backup_dir() / name
    if not f.exists():
        return error('Backup nicht gefunden', 404)
    f.unlink()
    return ok({'backups': _list_backups(_backup_dir())}, 'Backup gelöscht')


@admin_bp.route('/backup/<name>/restore', methods=['POST'])
@require_admin
def restore_backup(name):
    if not _validate_filename(name):
        return error('Ungültiger Dateiname', 400)
    if not name.endswith('.enc'):
        return error('Nur verschlüsselte .enc-Backups können wiederhergestellt werden', 400)
    f = _backup_dir() / name
    if not f.exists():
        return error('Backup nicht gefunden', 404)

    data = request.get_json() or {}
    admin_password = data.get('admin_password', '')
    if not admin_password or not g.current_user.check_password(admin_password):
        return error('Admin-Passwort ungültig', 403)

    try:
        key = _derive_aes_key()
        encrypted = f.read_bytes()
        signed = _decrypt(encrypted, key)
        sql_bytes = _verify_payload(signed, key)
        _restore_from_bytes(sql_bytes)
        current_app.logger.warning('Datenbank aus Backup wiederhergestellt: %s (Admin: %s)',
                                   name, getattr(g.current_user, 'email', '?'))
        return ok(message='Datenbank wiederhergestellt')
    except ValueError as e:
        current_app.logger.error('Restore abgebrochen: %s', e)
        return error('Backup-Integrität konnte nicht verifiziert werden', 400)
    except Exception:
        current_app.logger.exception('Restore fehlgeschlagen')
        return error('Backup-Wiederherstellung fehlgeschlagen', 500)


@admin_bp.route('/backup/<name>/download', methods=['GET'])
@require_admin
def download_backup(name):
    if not _validate_filename(name):
        return error('Ungültiger Dateiname', 400)
    f = _backup_dir() / name
    if not f.exists():
        return error('Backup nicht gefunden', 404)
    return send_file(str(f.resolve()), as_attachment=True, download_name=name)


@admin_bp.route('/backup/upload', methods=['POST'])
@require_admin
def upload_backup():
    if 'file' not in request.files:
        return error('Keine Datei übergeben', 400)
    file = request.files['file']
    name = secure_filename(file.filename or '')
    if not _validate_filename(name):
        return error('Nur .enc-Dateien erlaubt', 400)
    d = _backup_dir()
    _autorotate(d)
    file.save(str(d / name))
    current_app.logger.info('Backup hochgeladen: %s', name)
    return ok({'backups': _list_backups(d)}, 'Backup hochgeladen')


