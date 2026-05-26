"""Backup & Restore für Standdienst.

Format: .sdbackup
  [4B magic 'SDBK'][1B version=1][16B PBKDF2-salt][12B AES-GCM-nonce][N B AES-GCM-ciphertext]

Das AES-GCM-Ciphertext entschlüsselt zu einem gzip-komprimierten Tar-Archiv:
  metadata.json          – App-Version, Zeitstempel, DB-Typ
  db.sql                 – pg_dump (PostgreSQL) oder SQLAlchemy-INSERTs (SQLite)
  sensitive_fields.json  – Entschlüsselte EncryptedStr-Felder (für migrations-sichere Restore)
  uploads/               – Alle hochgeladenen Dateien
  dotenv                 – Kopie der .env (nur Referenz, wird beim Restore nicht eingespielt)
"""

import hashlib
import io
import json
import logging
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

from flask import current_app, g, request, send_file
from werkzeug.utils import secure_filename
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text

from . import admin_bp
from ...extensions import db, limiter
from ...utils.auth import require_admin
from ...utils.responses import ok, error

log = logging.getLogger(__name__)

_MAGIC = b'SDBK'
_VERSION = 1
_PBKDF2_ITER = 260_000
MAX_BACKUPS = 20


# ---------------------------------------------------------------------------
# Pfade & Verzeichnisse
# ---------------------------------------------------------------------------

def _backup_dir() -> Path:
    d = Path(current_app.config.get('BACKUP_DIR', 'backups'))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _upload_dir() -> Path:
    return Path(current_app.config.get('UPLOAD_FOLDER', 'uploads'))


def _api_root() -> Path:
    return Path(current_app.root_path).parent


def _env_file() -> Path:
    return _api_root().parent / '.env'


# ---------------------------------------------------------------------------
# Kryptographie
# ---------------------------------------------------------------------------

def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, _PBKDF2_ITER, dklen=32)


def _encrypt_payload(data: bytes, password: str) -> bytes:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(password, salt)
    ct = AESGCM(key).encrypt(nonce, data, None)
    return _MAGIC + bytes([_VERSION]) + salt + nonce + ct


def _decrypt_payload(raw: bytes, password: str) -> bytes:
    if not raw.startswith(_MAGIC):
        raise ValueError('Kein gültiges .sdbackup-Format (Magic fehlt)')
    off = len(_MAGIC)
    version = raw[off]
    if version != _VERSION:
        raise ValueError(f'Unbekannte Backup-Version: {version}')
    off += 1
    salt = raw[off:off + 16]
    nonce = raw[off + 16:off + 28]
    ct = raw[off + 28:]
    key = _derive_key(password, salt)
    try:
        return AESGCM(key).decrypt(nonce, ct, None)
    except Exception:
        raise ValueError('Entschlüsselung fehlgeschlagen – falsches Passwort?')


# ---------------------------------------------------------------------------
# Datenbankdump
# ---------------------------------------------------------------------------

def _is_postgres() -> bool:
    url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    return url.startswith('postgresql')


def _pg_params() -> dict:
    url = urlparse(current_app.config['SQLALCHEMY_DATABASE_URI'])
    return {
        'host': url.hostname or 'localhost',
        'port': str(url.port or 5432),
        'user': unquote(url.username or ''),
        'password': unquote(url.password or ''),
        'dbname': url.path.lstrip('/'),
    }


def _dump_pg() -> bytes:
    p = _pg_params()
    env = {**os.environ, 'PGPASSWORD': p['password']}
    result = subprocess.run(
        [
            'pg_dump',
            '-h', p['host'], '-p', p['port'], '-U', p['user'], '-d', p['dbname'],
            '--format=plain', '--data-only', '--no-owner',
            '--no-privileges', '--column-inserts', '--disable-triggers',
        ],
        capture_output=True, env=env, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f'pg_dump fehlgeschlagen: {result.stderr.decode()}')
    return result.stdout


def _dump_sqlalchemy() -> bytes:
    buf = io.StringIO()
    buf.write(f'-- Standdienst SQLite Backup {datetime.now(timezone.utc).isoformat()}\n')
    with db.engine.connect() as conn:
        for table in db.metadata.sorted_tables:
            rows = conn.execute(table.select()).fetchall()
            if not rows:
                continue
            cols = ', '.join(f'"{c}"' for c in table.columns.keys())
            for row in rows:
                vals = ', '.join(_sql_val(v) for v in row)
                buf.write(f'INSERT INTO "{table.name}" ({cols}) VALUES ({vals});\n')
    return buf.getvalue().encode()


def _sql_val(v) -> str:
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'TRUE' if v else 'FALSE'
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def _dump_database() -> bytes:
    if _is_postgres():
        return _dump_pg()
    return _dump_sqlalchemy()


# ---------------------------------------------------------------------------
# Sensitive Fields (EncryptedStr)
# ---------------------------------------------------------------------------

def _extract_sensitive_fields() -> dict:
    """Liest alle EncryptedStr-Felder im Klartext aus (werden beim Dump entschlüsselt)."""
    from ...models import GlobalSettings, MailSettings
    result = {'global_settings': {}, 'mail_settings': []}
    gs = GlobalSettings.query.first()
    if gs:
        result['global_settings'] = {
            'smb_password': gs.smb_password,
            'github_pat': gs.github_pat,
            'backup_password': gs.backup_password,
        }
    for ms in MailSettings.query.all():
        result['mail_settings'].append({'id': ms.id, 'mail_password': ms.mail_password})
    return result


def _apply_sensitive_fields(fields: dict) -> None:
    """Schreibt entschlüsselte Felder zurück (SQLAlchemy re-verschlüsselt mit aktuellem SECRET_KEY)."""
    from ...models import GlobalSettings, MailSettings
    gs = GlobalSettings.query.first()
    if gs and 'global_settings' in fields:
        gf = fields['global_settings']
        gs.smb_password = gf.get('smb_password')
        gs.github_pat = gf.get('github_pat')
        gs.backup_password = gf.get('backup_password')
        db.session.add(gs)
    for ms_data in fields.get('mail_settings', []):
        ms = MailSettings.query.get(ms_data['id'])
        if ms:
            ms.mail_password = ms_data.get('mail_password')
            db.session.add(ms)
    db.session.commit()


# ---------------------------------------------------------------------------
# Backup erstellen
# ---------------------------------------------------------------------------

def _get_backup_password() -> str:
    """Liest das Backup-Passwort aus GlobalSettings. Wirft ValueError wenn nicht gesetzt."""
    from ...models import GlobalSettings
    gs = GlobalSettings.query.first()
    pw = gs.backup_password if gs else None
    if not pw:
        raise ValueError('Kein Backup-Passwort konfiguriert. Bitte unter Backup-Einstellungen setzen.')
    return pw


def run_backup(label: str | None = None, password: str | None = None) -> str:
    """Erstellt ein .sdbackup-Archiv. Gibt den Dateinamen zurück."""
    if password is None:
        password = _get_backup_password()

    d = _backup_dir()
    _autorotate(d)

    # Metadaten
    from ...models import GlobalSettings
    gs = GlobalSettings.query.first()
    app_version = _read_version()
    metadata = {
        'format_version': _VERSION,
        'app_version': app_version,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'db_type': 'postgresql' if _is_postgres() else 'sqlite',
    }

    # Datenbankdump
    db_sql = _dump_database()

    # Sensitive Fields (entschlüsselt)
    sensitive = _extract_sensitive_fields()

    # Tar-Archiv im Speicher erstellen
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode='w:gz') as tf:
        _tar_add_bytes(tf, 'metadata.json', json.dumps(metadata, indent=2).encode())
        _tar_add_bytes(tf, 'db.sql', db_sql)
        _tar_add_bytes(tf, 'sensitive_fields.json', json.dumps(sensitive).encode())

        # uploads/
        upload_dir = _upload_dir()
        if upload_dir.exists():
            for f in upload_dir.rglob('*'):
                if f.is_file():
                    arcname = 'uploads/' + str(f.relative_to(upload_dir))
                    tf.add(str(f), arcname=arcname)

        # .env (nur Referenz)
        env_path = _env_file()
        if env_path.exists():
            tf.add(str(env_path), arcname='dotenv')

    # Verschlüsseln & speichern
    encrypted = _encrypt_payload(tar_buf.getvalue(), password)
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    suffix = f'_{label}' if label else ''
    name = f'standdienst_{ts}{suffix}.sdbackup'
    (d / name).write_bytes(encrypted)
    log.info('Backup erstellt: %s (%d Bytes)', name, len(encrypted))
    return name


def _tar_add_bytes(tf: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    tf.addfile(info, io.BytesIO(data))


def _read_version() -> str:
    try:
        vpath = _api_root() / 'version.py'
        m = re.search(r'VERSION\s*=\s*["\']([^"\']+)', vpath.read_text())
        return m.group(1) if m else 'unbekannt'
    except Exception:
        return 'unbekannt'


# ---------------------------------------------------------------------------
# Rotation & Lock
# ---------------------------------------------------------------------------

def _lock_file(f: Path) -> Path:
    return f.with_suffix(f.suffix + '.lock')


def _is_locked(f: Path) -> bool:
    return _lock_file(f).exists()


def _autorotate(d: Path) -> None:
    files = sorted(d.glob('*.sdbackup'), key=lambda f: f.stat().st_mtime)
    unlocked = [f for f in files if not _is_locked(f)]
    while len(files) >= MAX_BACKUPS and unlocked:
        unlocked[0].unlink()
        log.info('Backup rotiert: %s', unlocked[0].name)
        files.pop(0)
        unlocked.pop(0)


def _list_backups(d: Path) -> list[dict]:
    files = sorted(d.glob('*.sdbackup'), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {
            'filename': f.name,
            'size_bytes': f.stat().st_size,
            'created_at': datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
            'locked': _is_locked(f),
        }
        for f in files
    ]


def _validate_filename(name: str) -> bool:
    if not name or '/' in name or '..' in name or name.startswith('.'):
        return False
    return name.endswith('.sdbackup')


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------

def _restore_pg(sql_bytes: bytes) -> None:
    p = _pg_params()
    env = {**os.environ, 'PGPASSWORD': p['password']}
    base_cmd = ['psql', '-h', p['host'], '-p', p['port'], '-U', p['user'], '-d', p['dbname'],
                '-v', 'ON_ERROR_STOP=1', '--no-psqlrc', '-q']

    # FK-Constraints deaktivieren, alle Tabellen leeren
    tables = [t.name for t in reversed(db.metadata.sorted_tables)]
    truncate_sql = "SET session_replication_role = 'replica';\n"
    truncate_sql += 'TRUNCATE TABLE ' + ', '.join(f'"{t}"' for t in tables) + ' RESTART IDENTITY CASCADE;\n'
    truncate_sql += "SET session_replication_role = 'origin';\n"

    r = subprocess.run(base_cmd, input=truncate_sql.encode(), capture_output=True, env=env, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f'Tabellen leeren fehlgeschlagen: {r.stderr.decode()}')

    # Daten einspielen
    restore_sql = "SET session_replication_role = 'replica';\n" + sql_bytes.decode('utf-8') + "\nSET session_replication_role = 'origin';\n"
    r = subprocess.run(base_cmd, input=restore_sql.encode(), capture_output=True, env=env, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f'Daten-Restore fehlgeschlagen: {r.stderr.decode()}')


def _restore_sqlalchemy(sql_bytes: bytes) -> None:
    stmts = [
        line.strip()
        for line in sql_bytes.decode('utf-8').splitlines()
        if line.strip() and not line.startswith('--')
    ]
    with db.engine.begin() as conn:
        try:
            conn.execute(text("SET session_replication_role = 'replica'"))
        except Exception:
            pass
        for table in reversed(db.metadata.sorted_tables):
            conn.execute(table.delete())
        for stmt in stmts:
            conn.execute(text(stmt))
        try:
            conn.execute(text("SET session_replication_role = 'origin'"))
        except Exception:
            pass


def _fix_upload_permissions(upload_dir: Path) -> None:
    """Stellt Dateisystemberechtigungen für uploads/ wieder her."""
    service_user = 'standdienst'
    try:
        import pwd
        entry = pwd.getpwnam(service_user)
        uid, gid = entry.pw_uid, entry.pw_gid
        for root, dirs, files in os.walk(str(upload_dir)):
            os.chown(root, uid, gid)
            for f in files:
                os.chown(os.path.join(root, f), uid, gid)
    except (KeyError, PermissionError):
        pass  # Im Dev-Betrieb ignorieren


def _schedule_restart() -> None:
    """Startet den Dienst 2 Sekunden nach dem Restore neu (Hintergrundthread)."""
    def _do_restart():
        import time, shutil
        time.sleep(2)
        systemctl = shutil.which('systemctl') or 'systemctl'
        try:
            subprocess.run(['sudo', systemctl, 'restart', 'standdienst'],
                          timeout=30, capture_output=True)
        except Exception as e:
            log.warning('Dienst-Neustart fehlgeschlagen: %s', e)

    t = threading.Thread(target=_do_restart, daemon=True)
    t.start()


def run_restore(backup_path: Path, password: str) -> None:
    """Stellt ein Backup vollständig wieder her."""
    raw = backup_path.read_bytes()
    payload = _decrypt_payload(raw, password)

    with tempfile.TemporaryDirectory() as tmpdir:
        tar_buf = io.BytesIO(payload)
        with tarfile.open(fileobj=tar_buf, mode='r:gz') as tf:
            tf.extractall(tmpdir, filter='data')

        tmppath = Path(tmpdir)

        # Metadaten prüfen
        meta_file = tmppath / 'metadata.json'
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            log.info('Restore aus Backup v%s vom %s', meta.get('app_version'), meta.get('created_at'))

        # Datenbank wiederherstellen
        sql_file = tmppath / 'db.sql'
        if not sql_file.exists():
            raise ValueError('db.sql fehlt im Backup-Archiv')

        sql_bytes = sql_file.read_bytes()
        if _is_postgres():
            _restore_pg(sql_bytes)
        else:
            _restore_sqlalchemy(sql_bytes)

        # Sensitive Fields re-verschlüsseln
        sf_file = tmppath / 'sensitive_fields.json'
        if sf_file.exists():
            _apply_sensitive_fields(json.loads(sf_file.read_text()))

        # uploads/ wiederherstellen
        uploads_src = tmppath / 'uploads'
        upload_dir = _upload_dir()
        if uploads_src.exists():
            if upload_dir.exists():
                shutil.rmtree(str(upload_dir))
            shutil.copytree(str(uploads_src), str(upload_dir))
            _fix_upload_permissions(upload_dir)

    # Dienst neu starten (verzögert)
    _schedule_restart()


# ---------------------------------------------------------------------------
# API-Endpunkte
# ---------------------------------------------------------------------------

@admin_bp.route('/backup/settings', methods=['GET'])
@require_admin
def get_backup_settings():
    from ...models import GlobalSettings
    gs = GlobalSettings.query.first()
    has_password = bool(gs and gs.backup_password)
    return ok({'has_backup_password': has_password})


@admin_bp.route('/backup/settings', methods=['PUT'])
@require_admin
def update_backup_settings():
    from ...models import GlobalSettings
    data = request.get_json() or {}
    new_pw = data.get('backup_password', '').strip()
    if not new_pw:
        return error('Backup-Passwort darf nicht leer sein', 400)
    gs = GlobalSettings.query.first()
    if not gs:
        return error('GlobalSettings nicht gefunden', 500)
    gs.backup_password = new_pw
    db.session.commit()
    return ok(message='Backup-Passwort gesetzt')


@admin_bp.route('/backup/list', methods=['GET'])
@require_admin
def list_backups():
    return ok({'backups': _list_backups(_backup_dir()), 'max_backups': MAX_BACKUPS})


@admin_bp.route('/backup/create', methods=['POST'])
@require_admin
def create_backup():
    data = request.get_json() or {}
    password = data.get('backup_password') or None
    try:
        name = run_backup(password=password)
        return ok({'backups': _list_backups(_backup_dir()), 'created': name}, 'Backup erstellt')
    except ValueError as e:
        return error(str(e), 400)
    except Exception as e:
        log.exception('Backup fehlgeschlagen')
        return error(f'Backup fehlgeschlagen: {e}', 500)


@admin_bp.route('/backup/<name>/restore', methods=['POST'])
@require_admin
@limiter.limit('5 per minute')
def restore_backup(name):
    if not _validate_filename(name):
        return error('Ungültiger Dateiname', 400)
    f = _backup_dir() / name
    if not f.exists():
        return error('Backup nicht gefunden', 404)

    data = request.get_json() or {}
    admin_password = data.get('admin_password', '')
    if not admin_password or not g.current_user.check_password(admin_password):
        return error('Admin-Passwort ungültig', 403)

    backup_password = data.get('backup_password', '').strip()
    if not backup_password:
        # Passwort aus Einstellungen
        try:
            backup_password = _get_backup_password()
        except ValueError as e:
            return error(str(e), 400)

    try:
        run_restore(f, backup_password)
        log.warning('Backup wiederhergestellt: %s (Admin: %s)', name,
                    getattr(g.current_user, 'email', '?'))
        return ok(message='Backup wiederhergestellt – Anwendung wird neu gestartet')
    except ValueError as e:
        log.error('Restore abgebrochen: %s', e)
        return error(str(e), 400)
    except Exception:
        log.exception('Restore fehlgeschlagen')
        return error('Backup-Wiederherstellung fehlgeschlagen', 500)


@admin_bp.route('/backup/<name>', methods=['DELETE'])
@require_admin
def delete_backup(name):
    if not _validate_filename(name):
        return error('Ungültiger Dateiname', 400)
    f = _backup_dir() / name
    if not f.exists():
        return error('Backup nicht gefunden', 404)
    if _is_locked(f):
        return error('Backup ist gesperrt – zuerst entsperren', 409)
    f.unlink()
    return ok({'backups': _list_backups(_backup_dir())}, 'Backup gelöscht')


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
        return error('Nur .sdbackup-Dateien erlaubt', 400)
    d = _backup_dir()
    _autorotate(d)
    file.save(str(d / name))
    log.info('Backup hochgeladen: %s', name)
    return ok({'backups': _list_backups(d)}, 'Backup hochgeladen')


@admin_bp.route('/backup/<name>/lock', methods=['POST'])
@require_admin
def lock_backup(name):
    if not _validate_filename(name):
        return error('Ungültiger Dateiname', 400)
    f = _backup_dir() / name
    if not f.exists():
        return error('Backup nicht gefunden', 404)
    _lock_file(f).touch()
    return ok({'backups': _list_backups(_backup_dir())}, 'Backup gesperrt')


@admin_bp.route('/backup/<name>/lock', methods=['DELETE'])
@require_admin
def unlock_backup(name):
    if not _validate_filename(name):
        return error('Ungültiger Dateiname', 400)
    lf = _lock_file(_backup_dir() / name)
    if lf.exists():
        lf.unlink()
    return ok({'backups': _list_backups(_backup_dir())}, 'Backup entsperrt')
