import base64
import hashlib
import io
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g, request
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text

from . import admin_bp
from ...extensions import db
from ...utils.auth import require_admin
from ...utils.responses import ok, error

MAX_BACKUPS = 10


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
    files = sorted(backup_dir.glob('*.enc'), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {
            'filename': f.name,
            'size_bytes': f.stat().st_size,
            'created_at': datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
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


def _validate_filename(name: str) -> bool:
    return bool(name) and '/' not in name and not name.startswith('.') and name.endswith('.enc')


def run_backup() -> str:
    """Erstellt ein Backup und gibt den Dateinamen zurück. Wirft Exception bei Fehler."""
    d = _backup_dir()
    _autorotate(d)
    raw = _dump_database()
    encrypted = _encrypt(raw, _derive_aes_key())
    name = f'standdienst_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.enc'
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
    f = _backup_dir() / name
    if not f.exists():
        return error('Backup nicht gefunden', 404)
    try:
        encrypted = f.read_bytes()
        data = request.get_json() or {}
        key_b64 = data.get('key')
        key = base64.b64decode(key_b64) if key_b64 else _derive_aes_key()
        sql_bytes = _decrypt(encrypted, key)
        _restore_from_bytes(sql_bytes)
        current_app.logger.warning('Datenbank aus Backup wiederhergestellt: %s', name)
        return ok(message='Datenbank wiederhergestellt')
    except Exception as e:
        current_app.logger.exception('Restore fehlgeschlagen')
        return error(f'Restore fehlgeschlagen: {e}', 500)


@admin_bp.route('/backup/export-key', methods=['GET'])
@require_admin
def export_backup_key():
    key = _derive_aes_key()
    return ok({'key': base64.b64encode(key).decode()})
