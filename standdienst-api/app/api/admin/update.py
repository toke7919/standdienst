import subprocess
import sys
import os
import tarfile
import shutil
import tempfile
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone

from flask import current_app

from . import admin_bp
from ...utils.auth import require_admin
from ...utils.responses import ok, error


def _api_root() -> str:
    return os.path.normpath(os.path.join(current_app.root_path, '..'))


def _installed_version() -> str:
    ns: dict = {}
    try:
        with open(os.path.join(_api_root(), 'version.py')) as f:
            exec(f.read(), ns)  # noqa: S102
        return ns.get('VERSION', 'unbekannt')
    except OSError:
        return 'unbekannt'


def _version_tag(version: str) -> str:
    return version if version.startswith('v') else f'v{version}'


def _git_repo_slug() -> str | None:
    """Nur in Dev-Umgebungen mit .git-Verzeichnis verfügbar."""
    result = subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        capture_output=True, text=True, timeout=5, cwd=_api_root(),
    )
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    if 'github.com' not in url:
        return None
    path = url.split('github.com')[-1].lstrip('/:').removesuffix('.git')
    parts = path.split('/')
    return f'{parts[0]}/{parts[1]}' if len(parts) >= 2 else None


def _github_request(url: str, pat: str | None) -> dict | None:
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        **(({'Authorization': f'Bearer {pat}'}) if pat else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, ValueError):
        return None


def _github_latest_release(repo_slug: str, pat: str | None) -> dict | None:
    return _github_request(
        f'https://api.github.com/repos/{repo_slug}/releases/latest', pat
    )


def _github_release_notes(repo_slug: str, tag: str, pat: str | None) -> str:
    data = _github_request(
        f'https://api.github.com/repos/{repo_slug}/releases/tags/{tag}', pat
    )
    return data.get('body', '') if data else ''


def _is_newer(latest: str, current: str) -> bool:
    def _parts(v: str):
        v = v.lstrip('v').split('-')[0]
        try:
            return tuple(int(x) for x in v.split('.'))
        except ValueError:
            return (0,)
    return _parts(latest) > _parts(current)


def _download(url: str, dest: str, pat: str | None):
    req = urllib.request.Request(
        url, headers={'Authorization': f'Bearer {pat}'} if pat else {}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(dest, 'wb') as f:
            shutil.copyfileobj(resp, f)


def _repo_slug_and_pat():
    from ...models import GlobalSettings
    gs = GlobalSettings.query.first()
    pat = gs.github_pat if gs else None
    slug = (gs.github_repo if gs else None) or _git_repo_slug()
    return slug, pat


@admin_bp.route('/update/check', methods=['GET'])
@require_admin
def check_update():
    try:
        current_version = _installed_version()
        repo_slug, pat = _repo_slug_and_pat()

        if not repo_slug:
            return ok({
                'current_version': current_version,
                'current_release_notes': '',
                'update_available': False,
                'error': 'GitHub-Repository nicht konfiguriert (Einstellungen → Global)',
            })

        current_notes = _github_release_notes(repo_slug, _version_tag(current_version), pat)
        latest = _github_latest_release(repo_slug, pat)
        if latest is None:
            return ok({
                'current_version': current_version,
                'current_release_notes': current_notes,
                'update_available': False,
                'error': 'GitHub-Release-Abfrage fehlgeschlagen',
            })

        latest_version = latest.get('tag_name', '')
        return ok({
            'current_version': current_version,
            'current_release_notes': current_notes,
            'latest_version': latest_version,
            'latest_release_notes': latest.get('body', ''),
            'update_available': _is_newer(latest_version, current_version),
            'release_url': latest.get('html_url', ''),
        })
    except Exception as e:
        return error(f'Update-Check fehlgeschlagen: {e}', 500)


@admin_bp.route('/update/apply', methods=['POST'])
@require_admin
def apply_update():
    log = []
    try:
        _auto_backup(log)

        repo_slug, pat = _repo_slug_and_pat()
        if not repo_slug:
            return error('GitHub-Repository nicht konfiguriert (Einstellungen → Global)', 400)

        latest = _github_latest_release(repo_slug, pat)
        if not latest:
            return error('GitHub-Release-Abfrage fehlgeschlagen', 502)
        tarball_url = latest.get('tarball_url')
        if not tarball_url:
            return error('Kein Tarball im GitHub-Release gefunden', 500)

        _apply_tarball(tarball_url, pat, log)

        return ok({'log': log, 'applied_at': datetime.now(timezone.utc).isoformat()},
                  'Update angewendet – Dienst wird neu gestartet')
    except Exception as e:
        current_app.logger.exception('Update fehlgeschlagen')
        return error(f'Update fehlgeschlagen: {e}', 500)


def _auto_backup(log: list):
    try:
        from .backup import run_backup
        name = run_backup()
        log.append({'step': 'backup', 'ok': True, 'output': f'Backup erstellt: {name}'})
    except Exception as e:
        current_app.logger.warning('Backup vor Update fehlgeschlagen: %s', e)
        log.append({'step': 'backup', 'ok': False, 'output': f'Backup fehlgeschlagen (Update wird fortgesetzt): {e}'})


def _apply_tarball(tarball_url: str, pat: str | None, log: list):
    api_root = _api_root()
    project_root = os.path.normpath(os.path.join(api_root, '..'))

    with tempfile.TemporaryDirectory() as tmpdir:
        tar_path = os.path.join(tmpdir, 'release.tar.gz')
        _download(tarball_url, tar_path, pat)
        log.append({'step': 'download', 'ok': True, 'output': 'Release heruntergeladen'})

        with tarfile.open(tar_path) as tf:
            tf.extractall(tmpdir, filter='data')

        dirs = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
        if not dirs:
            raise RuntimeError('Entpacktes Verzeichnis nicht gefunden')
        extracted = os.path.join(tmpdir, dirs[0])
        log.append({'step': 'extract', 'ok': True, 'output': f'Entpackt: {dirs[0]}'})

        src_api = os.path.join(extracted, 'standdienst-api')
        if os.path.exists(src_api):
            shutil.copytree(src_api, api_root,
                            ignore=shutil.ignore_patterns('.env', 'uploads', 'backups', 'logs', '.venv', '__pycache__', '*.pyc'),
                            dirs_exist_ok=True)
            log.append({'step': 'copy', 'ok': True, 'output': 'API-Dateien überschrieben'})

        _rebuild_frontend(extracted, project_root, log)

    _run_step(['pip', 'install', '-r', 'requirements.txt', '-q'], api_root, 'pip install', log, use_python=True)
    _run_step(['flask', 'db', 'upgrade'], api_root, 'db upgrade', log,
              use_python=True, extra_env={'FLASK_APP': 'wsgi'})
    _run_step(['systemctl', 'restart', 'standdienst'], None, 'restart', log)


def _rebuild_frontend(extracted: str, project_root: str, log: list):
    src_fe = os.path.join(extracted, 'standdienst-frontend')
    fe_root = os.path.join(project_root, 'standdienst-frontend')
    if not (os.path.exists(src_fe) and os.path.exists(fe_root)):
        return
    shutil.copytree(src_fe, fe_root, dirs_exist_ok=True)
    subprocess.run(['npm', 'install'], capture_output=True, text=True, timeout=120, cwd=fe_root)
    build = subprocess.run(['npm', 'run', 'build'], capture_output=True, text=True, timeout=120, cwd=fe_root)
    log.append({'step': 'frontend', 'ok': build.returncode == 0, 'output': build.stdout + build.stderr})


def _run_step(cmd: list, cwd: str | None, label: str, log: list,
              use_python: bool = False, extra_env: dict | None = None):
    full_cmd = [sys.executable, '-m'] + cmd if use_python else cmd
    env = {**os.environ, **(extra_env or {})} if extra_env else None
    result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=180, cwd=cwd, env=env)
    log.append({'step': label, 'ok': result.returncode == 0, 'output': result.stdout + result.stderr})
