import base64
import io
import os
import subprocess
import tempfile
from datetime import datetime, timezone

from flask import current_app, g
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import admin_bp
from ...extensions import db
from ...models import GlobalSettings
from ...utils.auth import require_admin
from ...utils.responses import ok, error


def _derive_aes_key() -> bytes:
    import hashlib
    secret = current_app.config['SECRET_KEY']
    return hashlib.sha256(secret.encode()).digest()


def _encrypt_file(data: bytes) -> bytes:
    key = _derive_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext


def _smb_upload(settings: GlobalSettings, local_path: str, remote_name: str) -> None:
    cmd = [
        'smbclient',
        f'//{settings.smb_server}/{settings.smb_share}',
        '-U', f'{settings.smb_username}%{settings.smb_password}',
        '-c', f'cd "{settings.smb_path}"; put "{local_path}" "{remote_name}"',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f'smbclient Fehler: {result.stderr.strip()}')


@admin_bp.route('/backup/create', methods=['POST'])
@require_admin
def create_backup():
    settings = GlobalSettings.query.first()
    if not settings or not settings.smb_enabled:
        return error('SMB-Backup nicht konfiguriert oder deaktiviert', 400)

    required = [settings.smb_server, settings.smb_share, settings.smb_username]
    if not all(required):
        return error('SMB-Konfiguration unvollständig', 400)

    try:
        raw_data = _dump_database()
        encrypted = _encrypt_file(raw_data)

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        remote_name = f'standdienst_backup_{timestamp}.sql.enc'

        with tempfile.NamedTemporaryFile(delete=False, suffix='.enc') as tmp:
            tmp.write(encrypted)
            tmp_path = tmp.name

        try:
            _smb_upload(settings, tmp_path, remote_name)
        finally:
            os.unlink(tmp_path)

        return ok({'filename': remote_name, 'size_bytes': len(encrypted)},
                  'Backup erfolgreich erstellt')

    except Exception as e:
        current_app.logger.exception('Backup fehlgeschlagen')
        return error(f'Backup fehlgeschlagen: {e}', 500)


@admin_bp.route('/backup/test-connection', methods=['POST'])
@require_admin
def test_smb_connection():
    settings = GlobalSettings.query.first()
    if not settings or not settings.smb_server:
        return error('SMB nicht konfiguriert', 400)

    try:
        cmd = [
            'smbclient',
            f'//{settings.smb_server}/{settings.smb_share}',
            '-U', f'{settings.smb_username}%{settings.smb_password}',
            '-c', 'ls',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return error(f'Verbindung fehlgeschlagen: {result.stderr.strip()}', 400)
        return ok(message='Verbindung erfolgreich')
    except FileNotFoundError:
        return error('smbclient nicht gefunden – bitte installieren', 500)
    except subprocess.TimeoutExpired:
        return error('Timeout bei SMB-Verbindung', 408)


def _dump_database() -> bytes:
    """Creates a portable SQL dump of all data as INSERT statements."""
    from ...extensions import db as _db

    buf = io.StringIO()
    buf.write(f'-- Standdienst Backup {datetime.now(timezone.utc).isoformat()}\n')

    with _db.engine.connect() as conn:
        for table in _db.metadata.sorted_tables:
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
