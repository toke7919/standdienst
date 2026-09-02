"""Tests für app/api/admin/update.py – Update-Prüfung und -Mechanik.

apply_update() greift real ins Dateisystem ein (shutil.copytree auf den
API-Root), ruft `sudo systemctl restart` per subprocess und würde `pip
install`/`flask db upgrade` real ausführen. Das darf in Tests NIEMALS
unvermockt laufen – die gefährlichen Teilschritte (_apply_tarball,
_auto_backup, _set_maintenance_mode, _run_step) werden daher immer
gemockt. Nur die Orchestrierung (welcher Schritt wird wann mit welchem
Ergebnis aufgerufen) und die reinen Hilfsfunktionen werden getestet.
"""
import os
import tarfile
import tempfile
from unittest.mock import patch, MagicMock
from app.extensions import db as _db
from app.models import GlobalSettings
from app.api.admin import update as update_module
from app.api.admin.update import (
    _is_newer, _version_tag, _set_maintenance_mode, _auto_backup,
    _run_step, _download, _rebuild_frontend, _git_repo_slug, _resolve_github_api_ip,
    _apply_tarball,
)
from tests.conftest import login as _login


def _make_global_settings(github_repo='toke7919/standdienst', github_pat=None):
    gs = GlobalSettings(github_repo=github_repo, github_pat=github_pat)
    _db.session.add(gs)
    _db.session.commit()
    return gs


# ---------------------------------------------------------------------------
# Reine Hilfsfunktionen (kein Mocking nötig)
# ---------------------------------------------------------------------------

def test_is_newer_true_for_higher_version():
    assert _is_newer('v3.92.0', '3.91.0') is True


def test_is_newer_false_for_equal_version():
    assert _is_newer('v3.92.0', '3.92.0') is False


def test_is_newer_false_for_lower_version():
    assert _is_newer('v3.90.0', '3.92.0') is False


def test_is_newer_true_when_current_unparseable():
    # Unparseable Version wird als (0,) behandelt -> jede echte Version gilt als neuer
    # (sichere Fallback-Annahme: lieber ein Update zu viel anbieten als eins verpassen)
    assert _is_newer('v3.92.0', 'unbekannt') is True


def test_version_tag_adds_v_prefix():
    assert _version_tag('3.92.0') == 'v3.92.0'


def test_version_tag_keeps_existing_v_prefix():
    assert _version_tag('v3.92.0') == 'v3.92.0'


# ---------------------------------------------------------------------------
# GET /update/check
# ---------------------------------------------------------------------------

@patch('app.api.admin.update._git_repo_slug', return_value=None)
def test_check_update_no_repo_configured(mock_slug, client, admin_user):
    # _git_repo_slug() muss gemockt werden, sonst greift der Dev-Fallback auf
    # den echten `git remote` dieses Repos zu und der Test testet den falschen Pfad.
    _login(client, admin_user.email)
    rv = client.get('/api/admin/update/check')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['update_available'] is False
    assert 'nicht konfiguriert' in data['error']


@patch('app.api.admin.update._github_request')
def test_check_update_reports_available_update(mock_request, client, admin_user):
    _make_global_settings()
    mock_request.side_effect = [
        {'body': 'Alte Notizen'},  # _github_release_notes(current)
        {'tag_name': 'v99.0.0', 'body': 'Neue Notizen', 'html_url': 'https://example.test/release'},
    ]
    _login(client, admin_user.email)
    rv = client.get('/api/admin/update/check')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['update_available'] is True
    assert data['latest_version'] == 'v99.0.0'
    assert data['release_url'] == 'https://example.test/release'


@patch('app.api.admin.update._github_request')
def test_check_update_no_update_when_current(mock_request, client, admin_user):
    _make_global_settings()
    import version as _version_module
    mock_request.side_effect = [
        {'body': ''},
        {'tag_name': f'v{_version_module.VERSION}', 'body': '', 'html_url': ''},
    ]
    _login(client, admin_user.email)
    rv = client.get('/api/admin/update/check')
    assert rv.status_code == 200
    assert rv.get_json()['data']['update_available'] is False


@patch('app.api.admin.update._github_request')
def test_check_update_handles_github_unreachable(mock_request, client, admin_user):
    _make_global_settings()
    mock_request.side_effect = [{'body': ''}, None]
    _login(client, admin_user.email)
    rv = client.get('/api/admin/update/check')
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert data['update_available'] is False
    assert 'fehlgeschlagen' in data['error']


# ---------------------------------------------------------------------------
# POST /update/apply – Orchestrierung, alle gefährlichen Schritte gemockt
# ---------------------------------------------------------------------------

@patch('app.api.admin.update._git_repo_slug', return_value=None)
def test_apply_update_no_repo_configured(mock_slug, client, admin_user):
    # Ohne Mock würde der Dev-Fallback den echten `git remote` dieses Repos
    # finden und ein ECHTES Update anwenden (Download + systemctl restart!).
    _login(client, admin_user.email)
    rv = client.post('/api/admin/update/apply', json={})
    assert rv.status_code == 400


@patch('app.api.admin.update._github_request')
def test_apply_update_release_fetch_failed(mock_request, client, admin_user):
    _make_global_settings()
    mock_request.return_value = None
    _login(client, admin_user.email)
    rv = client.post('/api/admin/update/apply', json={})
    assert rv.status_code == 502


@patch('app.api.admin.update._github_request')
def test_apply_update_missing_tarball_url(mock_request, client, admin_user):
    _make_global_settings()
    mock_request.return_value = {'tag_name': 'v99.0.0'}  # kein tarball_url
    _login(client, admin_user.email)
    rv = client.post('/api/admin/update/apply', json={})
    assert rv.status_code == 500


@patch('app.api.admin.update._run_step')
@patch('app.api.admin.update._apply_tarball')
@patch('app.api.admin.update._auto_backup')
@patch('app.api.admin.update._set_maintenance_mode')
@patch('app.api.admin.update._github_request')
def test_apply_update_full_success_orchestration(
    mock_request, mock_maintenance, mock_backup, mock_apply_tarball, mock_run_step,
    client, admin_user,
):
    _make_global_settings()
    mock_request.return_value = {
        'tag_name': 'v99.0.0',
        'tarball_url': 'https://example.test/tarball.tar.gz',
    }
    _login(client, admin_user.email)
    rv = client.post('/api/admin/update/apply', json={})
    assert rv.status_code == 200
    data = rv.get_json()['data']
    assert 'applied_at' in data

    # Wartungsmodus wird vor UND nach dem Update umgeschaltet
    assert mock_maintenance.call_args_list[0].args[0] is True
    assert mock_maintenance.call_args_list[-1].args[0] is False
    mock_backup.assert_called_once()
    call_args = mock_apply_tarball.call_args.args
    assert call_args[0] == 'https://example.test/tarball.tar.gz'
    assert call_args[1] is None  # kein PAT konfiguriert
    assert isinstance(call_args[2], list)  # Log-Liste
    # Zwei Neustart-Schritte (Hauptdienst + Scheduler)
    assert mock_run_step.call_count == 2


@patch('app.api.admin.update._run_step')
@patch('app.api.admin.update._apply_tarball')
@patch('app.api.admin.update._auto_backup')
@patch('app.api.admin.update._set_maintenance_mode')
@patch('app.api.admin.update._github_request')
def test_apply_update_exception_during_tarball_returns_500(
    mock_request, mock_maintenance, mock_backup, mock_apply_tarball, mock_run_step,
    client, admin_user,
):
    _make_global_settings()
    mock_request.return_value = {
        'tag_name': 'v99.0.0',
        'tarball_url': 'https://example.test/tarball.tar.gz',
    }
    mock_apply_tarball.side_effect = RuntimeError('Entpacken fehlgeschlagen')
    _login(client, admin_user.email)
    rv = client.post('/api/admin/update/apply', json={})
    assert rv.status_code == 500


# ---------------------------------------------------------------------------
# _set_maintenance_mode – reine DB-Logik, kein Mocking nötig
# ---------------------------------------------------------------------------

def test_set_maintenance_mode_updates_global_settings():
    gs = _make_global_settings()
    log = []
    _set_maintenance_mode(True, log)
    _db.session.refresh(gs)
    assert gs.maintenance_mode is True
    assert log[0]['step'] == 'maintenance'
    assert log[0]['ok'] is True


def test_set_maintenance_mode_no_global_settings_row_logs_warning_not_crash():
    # Keine GlobalSettings angelegt -> gs ist None, Funktion darf nicht crashen
    log = []
    _set_maintenance_mode(True, log)
    assert log[0]['step'] == 'maintenance'
    assert log[0]['ok'] is True  # kein Fehler, nur nichts zu tun


# ---------------------------------------------------------------------------
# _auto_backup – run_backup() wird gemockt (erstellt sonst ein echtes Backup)
# ---------------------------------------------------------------------------

@patch('app.api.admin.backup.run_backup')
def test_auto_backup_success_logs_ok(mock_run_backup):
    mock_run_backup.return_value = 'backup-2027-01-01.sdbackup'
    log = []
    _auto_backup(log, target_version='99.0.0')
    assert log[0]['step'] == 'backup'
    assert log[0]['ok'] is True
    assert 'backup-2027-01-01.sdbackup' in log[0]['output']
    mock_run_backup.assert_called_once_with(label='vor_update_v99.0.0')


@patch('app.api.admin.backup.run_backup')
def test_auto_backup_failure_logs_ok_false_but_does_not_raise(mock_run_backup):
    mock_run_backup.side_effect = RuntimeError('kein Backup-Passwort gesetzt')
    log = []
    _auto_backup(log)  # darf nicht raisen, Update soll trotzdem weiterlaufen
    assert log[0]['step'] == 'backup'
    assert log[0]['ok'] is False
    assert 'kein Backup-Passwort gesetzt' in log[0]['output']


# ---------------------------------------------------------------------------
# _run_step – subprocess.run wird gemockt
# ---------------------------------------------------------------------------

@patch('app.api.admin.update.subprocess.run')
def test_run_step_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='ok\n', stderr='')
    log = []
    _run_step(['echo', 'hi'], None, 'testschritt', log)
    assert log[0]['step'] == 'testschritt'
    assert log[0]['ok'] is True
    assert 'ok' in log[0]['output']


@patch('app.api.admin.update.subprocess.run')
def test_run_step_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='Fehler!\n')
    log = []
    _run_step(['false'], None, 'testschritt', log)
    assert log[0]['ok'] is False
    assert 'Fehler!' in log[0]['output']


@patch('app.api.admin.update.subprocess.run')
def test_run_step_use_python_prefixes_interpreter(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
    _run_step(['pip', 'install', '-r', 'requirements.txt'], '/tmp', 'pip', [], use_python=True)
    called_cmd = mock_run.call_args.args[0]
    assert called_cmd[0] == update_module.sys.executable
    assert called_cmd[1] == '-m'


# ---------------------------------------------------------------------------
# _download – urllib.request.urlopen wird gemockt
# ---------------------------------------------------------------------------

def test_download_writes_response_body_to_dest():
    fake_body = b'release-tarball-bytes'

    class _FakeResponse:
        def __init__(self):
            self._served = False
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self, *a, **kw):
            # Muss wie ein echtes Response-Objekt EOF (b'') signalisieren, sonst
            # läuft shutil.copyfileobj() in _download() endlos und beschreibt
            # die Zieldatei unbegrenzt weiter (hat bereits zu einem Swap-Crash
            # der Dev-Maschine geführt).
            if self._served:
                return b''
            self._served = True
            return fake_body

    with patch('app.api.admin.update.urllib.request.urlopen', return_value=_FakeResponse()):
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, 'out.tar.gz')
            _download('https://example.test/release.tar.gz', dest, pat=None)
            with open(dest, 'rb') as f:
                assert f.read() == fake_body


# ---------------------------------------------------------------------------
# _rebuild_frontend – subprocess.run + shutil.which werden gemockt
# ---------------------------------------------------------------------------

def test_rebuild_frontend_missing_source_dir_logs_and_returns():
    with tempfile.TemporaryDirectory() as tmp:
        log = []
        _rebuild_frontend(tmp, log)  # 'standdienst-frontend' existiert nicht in tmp
        assert log[0]['step'] == 'frontend'
        assert log[0]['ok'] is False
        assert 'nicht im Release-Tarball enthalten' in log[0]['output']


@patch('app.api.admin.update.shutil.which', return_value=None)
def test_rebuild_frontend_npm_not_found(mock_which):
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, 'standdienst-frontend'))
        log = []
        _rebuild_frontend(tmp, log)
        assert log[0]['ok'] is False
        assert 'npm nicht gefunden' in log[0]['output']


@patch('app.api.admin.update.subprocess.run')
@patch('app.api.admin.update.shutil.which', return_value='/usr/bin/npm')
def test_rebuild_frontend_npm_install_fails(mock_which, mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='npm ERR!')
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, 'standdienst-frontend'))
        log = []
        _rebuild_frontend(tmp, log)
        assert log[0]['ok'] is False
        assert 'npm install fehlgeschlagen' in log[0]['output']


@patch('app.api.admin.update.subprocess.run')
@patch('app.api.admin.update.shutil.which', return_value='/usr/bin/npm')
def test_rebuild_frontend_success(mock_which, mock_run):
    # install (returncode 0), dann build (returncode 0)
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout='', stderr=''),
        MagicMock(returncode=0, stdout='built\n', stderr=''),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, 'standdienst-frontend'))
        log = []
        _rebuild_frontend(tmp, log)
        assert log[0]['ok'] is True
        assert 'built' in log[0]['output']


# ---------------------------------------------------------------------------
# _apply_tarball – End-to-End mit gemocktem Download/Frontend-Build/Copytree/Run-Step
# ---------------------------------------------------------------------------

def _make_fake_release_tarball(tmp_dir: str) -> str:
    """Baut ein minimales Tarball mit standdienst-api/version.py drin."""
    src_root = os.path.join(tmp_dir, 'toke7919-standdienst-abc1234')
    os.makedirs(os.path.join(src_root, 'standdienst-api'))
    with open(os.path.join(src_root, 'standdienst-api', 'version.py'), 'w') as f:
        f.write('VERSION = "99.0.0"\n')

    tar_path = os.path.join(tmp_dir, 'source.tar.gz')
    with tarfile.open(tar_path, 'w:gz') as tf:
        tf.add(src_root, arcname='toke7919-standdienst-abc1234')
    return tar_path


@patch('app.api.admin.update._run_step')
@patch('app.api.admin.update.shutil.copytree')
@patch('app.api.admin.update._rebuild_frontend')
@patch('app.api.admin.update._download')
def test_apply_tarball_extracts_and_copies_api_files(
    mock_download, mock_rebuild_frontend, mock_copytree, mock_run_step,
):
    with tempfile.TemporaryDirectory() as prep_dir:
        fake_tar = _make_fake_release_tarball(prep_dir)

        def _fake_download(url, dest, pat):
            # Simuliert den Download, indem das vorbereitete Tarball an dest kopiert wird
            import shutil as _shutil
            _shutil.copy(fake_tar, dest)

        mock_download.side_effect = _fake_download

        log = []
        _apply_tarball('https://example.test/tarball.tar.gz', None, log)

        mock_rebuild_frontend.assert_called_once()
        mock_copytree.assert_called_once()
        # Zwei _run_step-Aufrufe: pip install + flask db upgrade
        assert mock_run_step.call_count == 2

        steps = [l['step'] for l in log]
        assert 'download' in steps
        assert 'extract' in steps
        assert 'copy' in steps


@patch('app.api.admin.update._download')
def test_apply_tarball_raises_when_extracted_dir_empty(mock_download):
    def _fake_download(url, dest, pat):
        # Leeres Tarball -> kein Unterverzeichnis nach dem Entpacken
        with tarfile.open(dest, 'w:gz'):
            pass

    mock_download.side_effect = _fake_download
    log = []
    try:
        _apply_tarball('https://example.test/tarball.tar.gz', None, log)
        assert False, 'RuntimeError erwartet'
    except RuntimeError as e:
        assert 'Entpacktes Verzeichnis nicht gefunden' in str(e)


# ---------------------------------------------------------------------------
# _git_repo_slug – subprocess.run wird gemockt
# ---------------------------------------------------------------------------

@patch('app.api.admin.update.subprocess.run')
def test_git_repo_slug_parses_https_github_url(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='https://github.com/toke7919/standdienst.git\n')
    assert _git_repo_slug() == 'toke7919/standdienst'


@patch('app.api.admin.update.subprocess.run')
def test_git_repo_slug_parses_ssh_github_url(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='git@github.com:toke7919/standdienst.git\n')
    assert _git_repo_slug() == 'toke7919/standdienst'


@patch('app.api.admin.update.subprocess.run')
def test_git_repo_slug_none_for_non_github_remote(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='https://gitlab.com/foo/bar.git\n')
    assert _git_repo_slug() is None


@patch('app.api.admin.update.subprocess.run')
def test_git_repo_slug_none_when_no_git_repo(mock_run):
    mock_run.return_value = MagicMock(returncode=128, stdout='')
    assert _git_repo_slug() is None


# ---------------------------------------------------------------------------
# _resolve_github_api_ip – System-Resolver + dig-Fallback werden gemockt
# ---------------------------------------------------------------------------

@patch('socket.getaddrinfo')
def test_resolve_github_api_ip_uses_system_resolver(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(2, 1, 6, '', ('140.82.121.6', 443))]
    assert _resolve_github_api_ip() == '140.82.121.6'


@patch('app.api.admin.update.subprocess.run')
@patch('socket.getaddrinfo')
def test_resolve_github_api_ip_falls_back_to_dig(mock_getaddrinfo, mock_run):
    mock_getaddrinfo.side_effect = OSError('DNS kaputt')
    mock_run.return_value = MagicMock(stdout='140.82.121.6\n')
    assert _resolve_github_api_ip() == '140.82.121.6'


@patch('app.api.admin.update.subprocess.run')
@patch('socket.getaddrinfo')
def test_resolve_github_api_ip_returns_none_when_both_fail(mock_getaddrinfo, mock_run):
    mock_getaddrinfo.side_effect = OSError('DNS kaputt')
    mock_run.side_effect = Exception('dig nicht gefunden')
    assert _resolve_github_api_ip() is None
