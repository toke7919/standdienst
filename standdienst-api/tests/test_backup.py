"""Funktionale Tests für app/api/admin/backup.py.

Autorisierung (@require_admin) ist bereits in test_authz_backup.py abgedeckt.

Sicherheitsprüfung vorab (wie bei update.py) – gefundene reale Risiken und wie
damit umgegangen wird:

- BACKUP_DIR/UPLOAD_FOLDER sind in TestingConfig NICHT überschrieben (Default
  'backups'/'uploads', relativ zum cwd) -> jeder Test, der run_backup()/
  run_restore() real aufruft, biegt beide Pfade über die temp_backup_dirs-
  Fixture auf ein tempfile.TemporaryDirectory() um.
- _schedule_restart() startet einen Daemon-Thread, der nach 2s
  `sudo systemctl restart standdienst` aufruft (echter Subprocess, läuft
  außerhalb des Test-Requests weiter -> Race mit unittest.mock.patch). Wird in
  JEDEM Test, der run_restore() erreicht, explizit gemockt.
- _dump_pg()/_restore_pg() (echte pg_dump/psql-Subprocesse) werden in der
  SQLite-Testumgebung nie erreicht (_is_postgres() ist immer False); für die
  Coverage dieser Codepfade werden _is_postgres UND subprocess.run zusammen
  gemockt, niemals nur einer von beiden.
- POST /backup/<name>/restore startet die eigentliche Wiederherstellung in
  einem echten Hintergrund-Thread (asynchron, per Job-Status pollbar). Der
  HTTP-Endpunkt wird daher nur für die synchronen Validierungen getestet
  (die vor dem Thread-Start zurückkehren) bzw. mit gemocktem run_restore()
  (damit der Thread-Body sofort zurückkehrt). Die eigentliche Restore-Logik
  wird separat direkt über run_restore() getestet (kein Thread involviert).
"""
import io
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.extensions import db as _db
from app.models import Instance, GlobalSettings, SiteSettings
from app.api.admin import backup as backup_module
from app.api.admin.backup import (
    _validate_filename, _encrypt_payload, _decrypt_payload, _sql_val,
    _dump_sqlalchemy, _autorotate, _get_backup_password, _list_backups,
    run_backup, run_restore, MAX_BACKUPS,
)
from tests.conftest import login as _login


def _admin_client(client, admin_user):
    _login(client, admin_user.email)
    return client


@pytest.fixture
def temp_backup_dirs(app):
    """Verhindert, dass Backup-Tests echte Dateien in standdienst-api/backups/
    bzw. echte Uploads in standdienst-api/uploads/ lesen/schreiben."""
    with tempfile.TemporaryDirectory() as backup_dir, tempfile.TemporaryDirectory() as upload_dir:
        old_backup = app.config.get('BACKUP_DIR')
        old_upload = app.config.get('UPLOAD_FOLDER')
        app.config['BACKUP_DIR'] = backup_dir
        app.config['UPLOAD_FOLDER'] = upload_dir
        try:
            yield {'backup_dir': Path(backup_dir), 'upload_dir': Path(upload_dir)}
        finally:
            app.config['BACKUP_DIR'] = old_backup
            app.config['UPLOAD_FOLDER'] = old_upload


def _set_backup_password(password='SicheresBackupPass1!'):
    gs = GlobalSettings.query.first()
    if not gs:
        gs = GlobalSettings()
        _db.session.add(gs)
    gs.backup_password = password
    _db.session.commit()
    return password


# ---------------------------------------------------------------------------
# _validate_filename – sicherheitskritisch (Path Traversal)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('name,expected', [
    ('standdienst_20260101_120000.sdbackup', True),
    ('', False),
    ('kein-sdbackup.txt', False),
    ('../../../etc/passwd.sdbackup', False),
    ('foo/bar.sdbackup', False),
    ('.hidden.sdbackup', False),
    ('..sdbackup', False),
])
def test_validate_filename(name, expected):
    assert _validate_filename(name) is expected


# ---------------------------------------------------------------------------
# _encrypt_payload / _decrypt_payload – Roundtrip
# ---------------------------------------------------------------------------

def test_encrypt_decrypt_roundtrip():
    data = b'geheime-backup-daten'
    encrypted = _encrypt_payload(data, 'MeinPasswort1!')
    assert encrypted.startswith(b'SDBK')
    decrypted = _decrypt_payload(encrypted, 'MeinPasswort1!')
    assert decrypted == data


def test_decrypt_wrong_password_raises():
    encrypted = _encrypt_payload(b'daten', 'RichtigesPasswort')
    with pytest.raises(ValueError, match='Entschlüsselung fehlgeschlagen'):
        _decrypt_payload(encrypted, 'FalschesPasswort')


def test_decrypt_missing_magic_raises():
    with pytest.raises(ValueError, match='Magic fehlt'):
        _decrypt_payload(b'KEIN-GUELTIGES-FORMAT', 'egal')


def test_decrypt_unknown_version_raises():
    encrypted = bytearray(_encrypt_payload(b'x', 'pw'))
    encrypted[4] = 99  # Version-Byte manipulieren
    with pytest.raises(ValueError, match='Unbekannte Backup-Version'):
        _decrypt_payload(bytes(encrypted), 'pw')


# ---------------------------------------------------------------------------
# _sql_val / _dump_sqlalchemy
# ---------------------------------------------------------------------------

def test_sql_val_escapes_and_formats():
    assert _sql_val(None) == 'NULL'
    assert _sql_val(True) == 'TRUE'
    assert _sql_val(False) == 'FALSE'
    assert _sql_val(42) == '42'
    assert _sql_val("O'Brien") == "'O''Brien'"


def test_dump_sqlalchemy_contains_insert_for_populated_table(app, instance):
    dump = _dump_sqlalchemy().decode()
    assert f'INSERT INTO "instances"' in dump
    assert instance.slug in dump


# ---------------------------------------------------------------------------
# _autorotate
# ---------------------------------------------------------------------------

def test_autorotate_removes_oldest_unlocked_when_over_limit(tmp_path):
    import time
    for i in range(MAX_BACKUPS + 2):
        f = tmp_path / f'standdienst_{i:03d}.sdbackup'
        f.write_bytes(b'x')
        os_stat_workaround = f.stat()
        time.sleep(0.001)

    _autorotate(tmp_path)
    remaining = sorted(tmp_path.glob('*.sdbackup'))
    assert len(remaining) < MAX_BACKUPS + 2
    # Die ältesten (niedrigste Nummer) müssen weg sein
    assert 'standdienst_000.sdbackup' not in [f.name for f in remaining]


def test_autorotate_never_removes_locked_files(tmp_path):
    for i in range(MAX_BACKUPS + 2):
        f = tmp_path / f'standdienst_{i:03d}.sdbackup'
        f.write_bytes(b'x')
        f.with_suffix('.sdbackup.lock').touch()

    _autorotate(tmp_path)
    remaining = list(tmp_path.glob('*.sdbackup'))
    assert len(remaining) == MAX_BACKUPS + 2  # nichts gelöscht, alles gesperrt


# ---------------------------------------------------------------------------
# _get_backup_password
# ---------------------------------------------------------------------------

def test_get_backup_password_raises_when_not_configured(app):
    with pytest.raises(ValueError, match='Kein Backup-Passwort konfiguriert'):
        _get_backup_password()


def test_get_backup_password_returns_configured_value(app):
    _set_backup_password('MeinBackupPasswort1!')
    assert _get_backup_password() == 'MeinBackupPasswort1!'


# ---------------------------------------------------------------------------
# run_backup() + run_restore() – realer Roundtrip gegen SQLite (sicher)
# ---------------------------------------------------------------------------

def test_run_backup_raises_without_password(app, temp_backup_dirs):
    with pytest.raises(ValueError, match='Kein Backup-Passwort konfiguriert'):
        run_backup()


def test_run_backup_creates_encrypted_file_in_backup_dir(app, instance, temp_backup_dirs):
    password = _set_backup_password()
    name = run_backup(password=password)
    assert name.endswith('.sdbackup')
    created = temp_backup_dirs['backup_dir'] / name
    assert created.exists()
    assert created.read_bytes().startswith(b'SDBK')


def test_run_backup_includes_upload_files(app, instance, temp_backup_dirs):
    (temp_backup_dirs['upload_dir'] / 'logo.png').write_bytes(b'fake-png-bytes')
    password = _set_backup_password()
    name = run_backup(password=password)

    raw = (temp_backup_dirs['backup_dir'] / name).read_bytes()
    payload = _decrypt_payload(raw, password)
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as tf:
        names = tf.getnames()
    assert 'uploads/logo.png' in names


@patch('app.api.admin.backup._schedule_restart')
def test_run_restore_restores_data_and_uploads(mock_restart, app, instance, temp_backup_dirs):
    """Voller Roundtrip: Instanz-Daten + sensible Felder sichern, DB leeren, wiederherstellen."""
    from app.models import MailSettings
    (temp_backup_dirs['upload_dir'] / 'logo.png').write_bytes(b'fake-png-bytes')
    password = _set_backup_password()
    ms = MailSettings(mail_server='smtp.test', mail_password='geheimespasswort')
    _db.session.add(ms)
    _db.session.commit()

    name = run_backup(password=password)
    backup_path = temp_backup_dirs['backup_dir'] / name
    original_slug = instance.slug

    # DB "beschädigen" (alle Instanzen löschen), um die Wiederherstellung nachzuweisen
    _db.session.execute(Instance.__table__.delete())
    _db.session.commit()
    assert _db.session.query(Instance).count() == 0

    run_restore(backup_path, password)

    restored = _db.session.query(Instance).filter_by(slug=original_slug).first()
    assert restored is not None
    assert (temp_backup_dirs['upload_dir'] / 'logo.png').read_bytes() == b'fake-png-bytes'
    mock_restart.assert_called_once()  # Neustart wurde angestoßen, aber nicht real ausgeführt

    restored_gs = GlobalSettings.query.first()
    assert restored_gs.backup_password == password
    restored_ms = MailSettings.query.first()
    assert restored_ms.mail_password == 'geheimespasswort'


@patch('app.api.admin.backup._schedule_restart')
def test_run_restore_wrong_password_raises(mock_restart, app, instance, temp_backup_dirs):
    password = _set_backup_password()
    name = run_backup(password=password)
    backup_path = temp_backup_dirs['backup_dir'] / name

    with pytest.raises(ValueError, match='Entschlüsselung fehlgeschlagen'):
        run_restore(backup_path, 'FalschesPasswort')
    mock_restart.assert_not_called()


@patch('app.api.admin.backup._schedule_restart')
def test_run_restore_reports_progress(mock_restart, app, instance, temp_backup_dirs):
    password = _set_backup_password()
    name = run_backup(password=password)
    backup_path = temp_backup_dirs['backup_dir'] / name

    steps = []
    run_restore(backup_path, password, progress_cb=lambda step, pct, msg: steps.append(step))

    assert 'decrypt' in steps
    assert 'db_restore' in steps
    assert steps[-1] == 'restart'


# ---------------------------------------------------------------------------
# _dump_pg / _restore_pg – nur mit doppeltem Mock (is_postgres + subprocess)
# ---------------------------------------------------------------------------

@patch('app.api.admin.backup._schedule_restart')
def test_run_restore_missing_db_sql_raises(mock_restart, app, temp_backup_dirs):
    """Manipuliertes/unvollständiges Archiv ohne db.sql darf nicht crashen, sondern
    einen klaren Fehler liefern."""
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode='w:gz') as tf:
        info = tarfile.TarInfo(name='metadata.json')
        data = b'{}'
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))

    encrypted = _encrypt_payload(tar_buf.getvalue(), 'pw')
    backup_path = temp_backup_dirs['backup_dir'] / 'kaputt.sdbackup'
    backup_path.write_bytes(encrypted)

    with pytest.raises(ValueError, match='db.sql fehlt'):
        run_restore(backup_path, 'pw')
    mock_restart.assert_not_called()


@patch('app.api.admin.backup.subprocess.run')
@patch('app.api.admin.backup._is_postgres', return_value=True)
def test_dump_database_uses_pg_dump_when_postgres(mock_is_pg, mock_run, app):
    mock_run.return_value = MagicMock(returncode=0, stdout=b'-- pg dump output', stderr=b'')
    result = backup_module._dump_database()
    assert result == b'-- pg dump output'
    called_cmd = mock_run.call_args.args[0]
    assert called_cmd[0] == 'pg_dump'


@patch('app.api.admin.backup.subprocess.run')
@patch('app.api.admin.backup._is_postgres', return_value=True)
def test_dump_pg_failure_raises(mock_is_pg, mock_run, app):
    mock_run.return_value = MagicMock(returncode=1, stdout=b'', stderr=b'connection refused')
    with pytest.raises(RuntimeError, match='pg_dump fehlgeschlagen'):
        backup_module._dump_database()


@patch('app.api.admin.backup.subprocess.run')
@patch('app.api.admin.backup._is_postgres', return_value=True)
def test_restore_pg_failure_raises(mock_is_pg, mock_run, app):
    mock_run.return_value = MagicMock(returncode=1, stdout=b'', stderr=b'syntax error')
    with pytest.raises(RuntimeError, match='Datenbank-Restore fehlgeschlagen'):
        backup_module._restore_pg(b'INSERT INTO x VALUES (1);')


@patch('app.api.admin.backup.subprocess.run')
@patch('app.api.admin.backup._is_postgres', return_value=True)
def test_restore_pg_strips_session_replication_role_lines(mock_is_pg, mock_run, app):
    mock_run.return_value = MagicMock(returncode=0, stdout=b'', stderr=b'')
    backup_module._restore_pg(b"SET session_replication_role = 'replica';\nINSERT INTO x VALUES (1);")
    sent_sql = mock_run.call_args.kwargs['input'].decode()
    assert 'session_replication_role' not in sent_sql
    assert 'INSERT INTO x' in sent_sql


# ---------------------------------------------------------------------------
# GET /backup/settings, PUT /backup/settings
# ---------------------------------------------------------------------------

def test_get_backup_settings_reflects_configured_password(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/backup/settings')
    assert rv.status_code == 200
    assert rv.get_json()['data']['has_backup_password'] is False

    _set_backup_password()
    rv = c.get('/api/admin/backup/settings')
    assert rv.get_json()['data']['has_backup_password'] is True


def test_put_backup_settings_empty_password_rejected(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.put('/api/admin/backup/settings', json={'backup_password': '  '})
    assert rv.status_code == 400


def test_put_backup_settings_success(client, admin_user):
    _db.session.add(GlobalSettings())  # existiert nach echtem Setup immer; hier explizit für den Test
    _db.session.commit()
    c = _admin_client(client, admin_user)
    rv = c.put('/api/admin/backup/settings', json={'backup_password': 'NeuesPasswort1!'})
    assert rv.status_code == 200
    gs = GlobalSettings.query.first()
    assert gs.backup_password == 'NeuesPasswort1!'


def test_put_backup_settings_without_global_settings_returns_500(client, admin_user):
    """Defensiver Pfad: GlobalSettings fehlt nach echtem Setup nie, aber der Code
    darf hier nicht crashen, sondern muss einen klaren Fehler liefern."""
    c = _admin_client(client, admin_user)
    rv = c.put('/api/admin/backup/settings', json={'backup_password': 'NeuesPasswort1!'})
    assert rv.status_code == 500


# ---------------------------------------------------------------------------
# GET /backup/list, POST /backup/create
# ---------------------------------------------------------------------------

def test_list_backups_empty(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/backup/list')
    assert rv.status_code == 200
    assert rv.get_json()['data']['backups'] == []
    assert rv.get_json()['data']['max_backups'] == MAX_BACKUPS


def test_create_backup_without_password_returns_400(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/backup/create', json={})
    assert rv.status_code == 400


def test_create_backup_success(client, admin_user, instance, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/backup/create', json={'backup_password': 'SicheresPasswort1!'})
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['created'].endswith('.sdbackup')
    assert len(data['backups']) == 1


@patch('app.api.admin.backup._dump_database', side_effect=RuntimeError('Datenbank nicht erreichbar'))
def test_create_backup_failure_returns_500(mock_dump, client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/backup/create', json={'backup_password': 'SicheresPasswort1!'})
    assert rv.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /backup/<name>
# ---------------------------------------------------------------------------

def test_delete_backup_invalid_filename_returns_400(client, admin_user, temp_backup_dirs):
    """Flasks <name>-Routenkonverter lässt ohnehin keine '/' zu; hier wird der
    _validate_filename()-Zweig für einen Namen ohne .sdbackup-Endung geprüft."""
    c = _admin_client(client, admin_user)
    rv = c.delete('/api/admin/backup/nicht-erlaubt.txt')
    assert rv.status_code == 400


def test_delete_backup_not_found_returns_404(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.delete('/api/admin/backup/nicht-vorhanden.sdbackup')
    assert rv.status_code == 404


def test_delete_backup_locked_returns_409(client, admin_user, instance, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    name = run_backup(password=_set_backup_password())
    c.post(f'/api/admin/backup/{name}/lock')

    rv = c.delete(f'/api/admin/backup/{name}')
    assert rv.status_code == 409


def test_delete_backup_success(client, admin_user, instance, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    name = run_backup(password=_set_backup_password())

    rv = c.delete(f'/api/admin/backup/{name}')
    assert rv.status_code == 200
    assert not (temp_backup_dirs['backup_dir'] / name).exists()


# ---------------------------------------------------------------------------
# GET /backup/<name>/download
# ---------------------------------------------------------------------------

def test_download_backup_invalid_filename_returns_400(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/backup/nicht-erlaubt.txt/download')
    assert rv.status_code == 400


def test_download_backup_not_found_returns_404(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/backup/nicht-vorhanden.sdbackup/download')
    assert rv.status_code == 404


def test_download_backup_success(client, admin_user, instance, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    name = run_backup(password=_set_backup_password())

    rv = c.get(f'/api/admin/backup/{name}/download')
    assert rv.status_code == 200
    assert rv.data.startswith(b'SDBK')


# ---------------------------------------------------------------------------
# POST /backup/upload
# ---------------------------------------------------------------------------

def test_upload_backup_no_file_returns_400(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/backup/upload', data={})
    assert rv.status_code == 400


def test_upload_backup_invalid_extension_returns_400(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/backup/upload', data={
        'file': (io.BytesIO(b'egal'), 'nicht-erlaubt.txt'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 400


def test_upload_backup_success(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    content = _encrypt_payload(b'irgendwelche-daten', 'pw')
    rv = c.post('/api/admin/backup/upload', data={
        'file': (io.BytesIO(content), 'hochgeladen.sdbackup'),
    }, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert (temp_backup_dirs['backup_dir'] / 'hochgeladen.sdbackup').exists()


# ---------------------------------------------------------------------------
# POST/DELETE /backup/<name>/lock
# ---------------------------------------------------------------------------

def test_lock_and_unlock_backup(client, admin_user, instance, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    name = run_backup(password=_set_backup_password())

    rv = c.post(f'/api/admin/backup/{name}/lock')
    assert rv.status_code == 200
    assert rv.get_json()['data']['backups'][0]['locked'] is True

    rv = c.delete(f'/api/admin/backup/{name}/lock')
    assert rv.status_code == 200
    assert rv.get_json()['data']['backups'][0]['locked'] is False


def test_lock_backup_not_found_returns_404(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/backup/nicht-vorhanden.sdbackup/lock')
    assert rv.status_code == 404


def test_lock_backup_invalid_filename_returns_400(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/backup/nicht-erlaubt.txt/lock')
    assert rv.status_code == 400


def test_unlock_backup_invalid_filename_returns_400(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.delete('/api/admin/backup/nicht-erlaubt.txt/lock')
    assert rv.status_code == 400


# ---------------------------------------------------------------------------
# POST /backup/<name>/restore – nur synchrone Validierung + gemocktes run_restore
# ---------------------------------------------------------------------------

def test_restore_invalid_filename_returns_400(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/backup/nicht-erlaubt.txt/restore', json={})
    assert rv.status_code == 400


def test_restore_not_found_returns_404(client, admin_user, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    rv = c.post('/api/admin/backup/nicht-vorhanden.sdbackup/restore', json={})
    assert rv.status_code == 404


def test_restore_wrong_admin_password_returns_403(client, admin_user, instance, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    name = run_backup(password=_set_backup_password())

    rv = c.post(f'/api/admin/backup/{name}/restore', json={'admin_password': 'FalschesPasswort'})
    assert rv.status_code == 403


def test_restore_no_backup_password_available_returns_400(client, admin_user, instance, temp_backup_dirs):
    c = _admin_client(client, admin_user)
    # Backup mit Passwort erstellen, Passwort danach aus GlobalSettings entfernen
    name = run_backup(password=_set_backup_password())
    gs = GlobalSettings.query.first()
    gs.backup_password = None
    _db.session.commit()

    rv = c.post(f'/api/admin/backup/{name}/restore', json={'admin_password': 'TestPass1!'})
    assert rv.status_code == 400


@patch('app.api.admin.backup.run_restore')
def test_restore_success_returns_job_id_without_running_real_restore(mock_run_restore, client, admin_user, instance, temp_backup_dirs):
    """run_restore() wird gemockt, damit der Hintergrund-Thread nie echten Code (inkl.
    _schedule_restart -> sudo systemctl restart) erreicht."""
    c = _admin_client(client, admin_user)
    name = run_backup(password=_set_backup_password())

    rv = c.post(f'/api/admin/backup/{name}/restore', json={
        'admin_password': 'TestPass1!', 'backup_password': 'SicheresBackupPass1!',
    })
    assert rv.status_code == 200
    assert 'job_id' in rv.get_json()['data']

    import time
    for _ in range(50):
        if mock_run_restore.called:
            break
        time.sleep(0.05)
    mock_run_restore.assert_called_once()


@patch('app.api.admin.backup.run_restore', side_effect=ValueError('Falsches Passwort'))
def test_restore_async_failure_reflected_in_job_status(mock_run_restore, client, admin_user, instance, temp_backup_dirs):
    """Wenn run_restore() im Hintergrund-Thread fehlschlägt, muss der Job-Status
    das melden statt den Fehler stillschweigend zu verschlucken."""
    c = _admin_client(client, admin_user)
    name = run_backup(password=_set_backup_password())

    rv = c.post(f'/api/admin/backup/{name}/restore', json={
        'admin_password': 'TestPass1!', 'backup_password': 'SicheresBackupPass1!',
    })
    job_id = rv.get_json()['data']['job_id']

    import time
    status = {}
    for _ in range(50):
        rv2 = c.get(f'/api/admin/backup/restore-status/{job_id}')
        status = rv2.get_json()['data']
        if status.get('done'):
            break
        time.sleep(0.05)

    assert status['done'] is True
    assert status['error'] == 'Falsches Passwort'


# ---------------------------------------------------------------------------
# GET /backup/restore-status/<job_id>
# ---------------------------------------------------------------------------

def test_restore_status_not_found_returns_404(client, admin_user):
    c = _admin_client(client, admin_user)
    rv = c.get('/api/admin/backup/restore-status/unbekannte-id')
    assert rv.status_code == 404
