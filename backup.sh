#!/usr/bin/env bash
# Standdienst – Backup-Script
# Erstellt ein .sdbackup-Backup über die interne Python-API (gleiche Logik wie Webinterface).
#
# Verwendung: ./backup.sh [--dir /pfad/zu/standdienst] [--label bezeichnung]
#   --dir    Installationsverzeichnis (Standard: Verzeichnis dieses Scripts)
#   --label  Optionale Bezeichnung im Dateinamen
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}"
LABEL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dir)   INSTALL_DIR="$2"; shift 2 ;;
        --label) LABEL="$2"; shift 2 ;;
        *) echo "Unbekannte Option: $1" >&2; exit 1 ;;
    esac
done

ENV_FILE="${INSTALL_DIR}/.env"
[[ -f "${ENV_FILE}" ]] || { echo "Fehler: .env nicht gefunden: ${ENV_FILE}" >&2; exit 1; }

set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

PYTHON="${INSTALL_DIR}/.venv/bin/python3"
[[ -x "${PYTHON}" ]] || { echo "Fehler: Python-Venv nicht gefunden: ${PYTHON}" >&2; exit 1; }
[[ -n "${SECRET_KEY:-}" ]]   || { echo "Fehler: SECRET_KEY fehlt in .env" >&2; exit 1; }
[[ -n "${DATABASE_URL:-}" ]] || { echo "Fehler: DATABASE_URL fehlt in .env" >&2; exit 1; }

"${PYTHON}" - <<PYEOF
import sys, os
sys.path.insert(0, '${INSTALL_DIR}/standdienst-api')

# Flask-App-Kontext aufbauen
from wsgi import app
with app.app_context():
    from app.api.admin.backup import run_backup
    label = '${LABEL}' or None
    try:
        name = run_backup(label=label)
        print(f'Backup erstellt: {name}')
    except Exception as e:
        print(f'Fehler: {e}', file=sys.stderr)
        sys.exit(1)
PYEOF
