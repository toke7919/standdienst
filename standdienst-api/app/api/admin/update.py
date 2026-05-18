import subprocess
import sys
import os
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone

from flask import current_app

from . import admin_bp
from ...utils.auth import require_admin
from ...utils.responses import ok, error


@admin_bp.route('/update/check', methods=['GET'])
@require_admin
def check_update():
    try:
        current_version = _installed_version()

        from ...models import GlobalSettings
        gs = GlobalSettings.query.first()
        pat = gs.github_pat if gs else None
        repo_slug = (gs.github_repo if gs else None) or _git_repo_slug(_repo_root())

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
        update_available = _is_newer(latest_version, current_version)
        return ok({
            'current_version': current_version,
            'current_release_notes': current_notes,
            'latest_version': latest_version,
            'latest_release_notes': latest.get('body', ''),
            'update_available': update_available,
            'release_url': latest.get('html_url', ''),
        })
    except Exception as e:
        return error(f'Update-Check fehlgeschlagen: {e}', 500)


def _installed_version() -> str:
    version_path = os.path.join(current_app.root_path, '..', 'version.py')
    ns: dict = {}
    try:
        with open(version_path) as f:
            exec(f.read(), ns)  # noqa: S102
        return ns.get('VERSION', 'unbekannt')
    except OSError:
        return _git_current_version(_repo_root())


def _version_tag(version: str) -> str:
    return version if version.startswith('v') else f'v{version}'


def _git_current_version(root: str) -> str:
    result = subprocess.run(
        ['git', 'describe', '--tags', '--always'],
        capture_output=True, text=True, timeout=5, cwd=root,
    )
    return result.stdout.strip() if result.returncode == 0 else 'unbekannt'


def _git_repo_slug(root: str) -> str | None:
    """Extrahiert owner/repo aus git remote origin – funktioniert nur in Dev-Umgebung."""
    result = subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        capture_output=True, text=True, timeout=5, cwd=root,
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


@admin_bp.route('/update/apply', methods=['POST'])
@require_admin
def apply_update():
    log = []
    try:
        # Automatisches Backup vor dem Update
        try:
            from .backup import run_backup
            backup_name = run_backup()
            log.append({'step': 'backup', 'ok': True, 'output': f'Backup erstellt: {backup_name}'})
        except Exception as be:
            current_app.logger.warning('Backup vor Update fehlgeschlagen: %s', be)
            log.append({'step': 'backup', 'ok': False, 'output': f'Backup fehlgeschlagen (Update wird fortgesetzt): {be}'})

        root = _repo_root()

        fetch = subprocess.run(
            ['git', 'fetch', 'origin', 'main'],
            capture_output=True, text=True, timeout=60, cwd=root,
        )
        log.append({'step': 'git fetch', 'ok': fetch.returncode == 0, 'output': fetch.stdout + fetch.stderr})
        if fetch.returncode != 0:
            return error('git fetch fehlgeschlagen', 500, {'log': log})

        pull = subprocess.run(
            ['git', 'pull', '--ff-only', 'origin', 'main'],
            capture_output=True, text=True, timeout=60, cwd=root,
        )
        log.append({'step': 'git pull', 'ok': pull.returncode == 0, 'output': pull.stdout + pull.stderr})
        if pull.returncode != 0:
            return error('git pull fehlgeschlagen', 500, {'log': log})

        pip_install = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '-q'],
            capture_output=True, text=True, timeout=180, cwd=root,
        )
        log.append({'step': 'pip install', 'ok': pip_install.returncode == 0,
                    'output': pip_install.stdout + pip_install.stderr})

        return ok({'log': log, 'applied_at': datetime.now(timezone.utc).isoformat()},
                  'Update angewendet – bitte neu starten')

    except Exception as e:
        current_app.logger.exception('Update fehlgeschlagen')
        return error(f'Update fehlgeschlagen: {e}', 500)


def _repo_root() -> str:
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        capture_output=True, text=True, timeout=5,
    )
    return result.stdout.strip() if result.returncode == 0 else os.getcwd()
