import subprocess
import sys
import os
import re
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
    try:
        with open(os.path.join(_api_root(), 'version.py')) as f:
            m = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', f.read(), re.M)
        return m.group(1) if m else 'unbekannt'
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


def _resolve_github_api_ip() -> str | None:
    """Löst api.github.com auf – bei Systemresolver-Ausfall via 8.8.8.8."""
    import socket
    import subprocess
    # 1. Systemresolver
    try:
        return socket.getaddrinfo('api.github.com', 443, socket.AF_INET)[0][4][0]
    except OSError:
        pass
    # 2. dig @8.8.8.8
    try:
        out = subprocess.run(
            ['dig', '+short', '+time=3', '+tries=1', '@8.8.8.8', 'api.github.com'],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        ip = next((l for l in out.splitlines() if l.count('.') == 3), None)
        if ip:
            return ip
    except Exception:
        pass
    return None


def _github_request(url: str, pat: str | None) -> dict | None:
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if pat:
        headers['Authorization'] = f'Bearer {pat}'

    def _fetch(target_url: str) -> dict | None:
        req = urllib.request.Request(target_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, ValueError):
            return None

    result = _fetch(url)
    if result is not None:
        return result

    # DNS-Fallback: IP über externen Resolver, URL-Host durch IP ersetzen
    ip = _resolve_github_api_ip()
    if ip:
        fallback = url.replace('https://api.github.com', f'https://{ip}', 1)
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False  # IP statt Hostname
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(fallback, headers={**headers, 'Host': 'api.github.com'})
        try:
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                return json.loads(resp.read())
        except Exception:
            pass
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
    # Priorität: DB-Einstellung → Env-Variable (von install.sh gesetzt) → git-Erkennung (Dev)
    slug = (gs.github_repo if gs else None) or os.environ.get('GITHUB_REPO') or _git_repo_slug()
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
    except Exception:
        current_app.logger.exception('Update-Check fehlgeschlagen')
        return error('Update-Check fehlgeschlagen', 500)


@admin_bp.route('/update/apply', methods=['POST'])
@require_admin
def apply_update():
    log = []
    try:
        repo_slug, pat = _repo_slug_and_pat()
        if not repo_slug:
            return error('GitHub-Repository nicht konfiguriert (Einstellungen → Global)', 400)

        latest = _github_latest_release(repo_slug, pat)
        if not latest:
            return error('GitHub-Release-Abfrage fehlgeschlagen', 502)
        tarball_url = latest.get('tarball_url')
        if not tarball_url:
            return error('Kein Tarball im GitHub-Release gefunden', 500)

        _set_maintenance_mode(True, log)
        target_version = latest.get('tag_name', '').lstrip('v')
        _auto_backup(log, target_version)
        _apply_tarball(tarball_url, pat, log)
        _set_maintenance_mode(False, log)

        systemctl = shutil.which('systemctl') or 'systemctl'
        _run_step(['sudo', systemctl, 'restart', 'standdienst'], None, 'restart', log)

        return ok({'log': log, 'applied_at': datetime.now(timezone.utc).isoformat()},
                  'Update angewendet – Dienst wird neu gestartet')
    except Exception:
        current_app.logger.exception('Update fehlgeschlagen')
        return error('Update fehlgeschlagen', 500)


def _set_maintenance_mode(enabled: bool, log: list | None = None):
    try:
        from ...models import GlobalSettings
        from ...extensions import db
        from ...utils.settings_cache import invalidate_global
        gs = GlobalSettings.query.first()
        if gs:
            gs.maintenance_mode = enabled
            db.session.commit()
            invalidate_global()
        if log is not None:
            log.append({'step': 'maintenance', 'ok': True,
                        'output': f'Wartungsmodus {"aktiviert" if enabled else "deaktiviert"}'})
    except Exception as e:
        current_app.logger.warning('Wartungsmodus konnte nicht gesetzt werden: %s', e)
        if log is not None:
            log.append({'step': 'maintenance', 'ok': False, 'output': str(e)})


def _auto_backup(log: list, target_version: str | None = None):
    try:
        from .backup import run_backup
        label = f'vor_update_v{target_version}' if target_version else 'vor_update'
        name = run_backup(label=label)
        log.append({'step': 'backup', 'ok': True, 'output': f'Backup erstellt: {name}'})
    except Exception as e:
        current_app.logger.warning('Backup vor Update fehlgeschlagen: %s', e)
        log.append({'step': 'backup', 'ok': False, 'output': f'Backup fehlgeschlagen (Update wird fortgesetzt): {e}'})


def _apply_tarball(tarball_url: str, pat: str | None, log: list):
    api_root = _api_root()

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

        # Frontend zuerst bauen – Output landet in extracted/standdienst-api/static/dist/
        _rebuild_frontend(extracted, log)

        src_api = os.path.join(extracted, 'standdienst-api')
        if os.path.exists(src_api):
            shutil.copytree(src_api, api_root,
                            ignore=shutil.ignore_patterns('.env', 'uploads', 'backups', 'logs', '.venv', '__pycache__', '*.pyc'),
                            dirs_exist_ok=True)
            log.append({'step': 'copy', 'ok': True, 'output': 'API-Dateien überschrieben'})

    _run_step(['pip', 'install', '-r', 'requirements.txt', '-q'], api_root, 'pip install', log, use_python=True)
    _run_step(['flask', 'db', 'upgrade'], api_root, 'db upgrade', log,
              use_python=True, extra_env={'FLASK_APP': 'wsgi'})


def _rebuild_frontend(extracted: str, log: list):
    """Baut das Frontend aus dem extrahierten Tarball.

    vite baut nach ../standdienst-api/static/dist/ (relativ zum Frontend-Verzeichnis),
    also landet der Output in extracted/standdienst-api/static/dist/ und wird
    anschließend durch copytree mit in die Produktion übernommen.
    """
    src_fe = os.path.join(extracted, 'standdienst-frontend')
    if not os.path.exists(src_fe):
        log.append({'step': 'frontend', 'ok': False,
                    'output': 'standdienst-frontend/ nicht im Release-Tarball enthalten – Frontend nicht aktualisiert'})
        return

    npm = shutil.which('npm')
    if not npm:
        log.append({'step': 'frontend', 'ok': False,
                    'output': 'npm nicht gefunden – Frontend nicht aktualisiert'})
        return

    install = subprocess.run([npm, 'install', '--silent'],
                             capture_output=True, text=True, timeout=180, cwd=src_fe)
    if install.returncode != 0:
        log.append({'step': 'frontend', 'ok': False,
                    'output': f'npm install fehlgeschlagen:\n{install.stderr}'})
        return

    build = subprocess.run([npm, 'run', 'build'],
                           capture_output=True, text=True, timeout=180, cwd=src_fe)
    log.append({'step': 'frontend', 'ok': build.returncode == 0,
                'output': build.stdout + build.stderr})


def _run_step(cmd: list, cwd: str | None, label: str, log: list,
              use_python: bool = False, extra_env: dict | None = None):
    full_cmd = [sys.executable, '-m'] + cmd if use_python else cmd
    env = {**os.environ, **(extra_env or {})} if extra_env else None
    result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=180, cwd=cwd, env=env)
    log.append({'step': label, 'ok': result.returncode == 0, 'output': result.stdout + result.stderr})
