import subprocess
import sys
import os
from datetime import datetime, timezone

from flask import current_app

from . import admin_bp
from ...utils.auth import require_admin
from ...utils.responses import ok, error


@admin_bp.route('/update/check', methods=['GET'])
@require_admin
def check_update():
    try:
        result = subprocess.run(
            ['git', 'fetch', '--dry-run'],
            capture_output=True, text=True, timeout=15,
            cwd=_repo_root(),
        )
        behind = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD..origin/main'],
            capture_output=True, text=True, timeout=10,
            cwd=_repo_root(),
        )
        commits_behind = int(behind.stdout.strip()) if behind.returncode == 0 else 0

        current = subprocess.run(
            ['git', 'describe', '--tags', '--always'],
            capture_output=True, text=True, timeout=5,
            cwd=_repo_root(),
        )

        return ok({
            'current_version': current.stdout.strip(),
            'commits_behind': commits_behind,
            'update_available': commits_behind > 0,
        })
    except Exception as e:
        return error(f'Update-Check fehlgeschlagen: {e}', 500)


@admin_bp.route('/update/apply', methods=['POST'])
@require_admin
def apply_update():
    try:
        root = _repo_root()
        log = []

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
