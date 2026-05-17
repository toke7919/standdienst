#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$REPO_ROOT/standdienst-api"
FRONTEND_DIR="$REPO_ROOT/standdienst-frontend"

echo "==> Standdienst v2 – Installation"

# ---------------------------------------------------------------------------
# Python-Backend
# ---------------------------------------------------------------------------
echo ""
echo "[1/4] Python-Abhängigkeiten installieren…"
cd "$API_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo "      ✓ Python-Abhängigkeiten installiert"

# ---------------------------------------------------------------------------
# Datenbankmigrationen
# ---------------------------------------------------------------------------
echo ""
echo "[2/4] Datenbankmigrationen ausführen…"

if [ -d "migrations" ]; then
    .venv/bin/flask --app wsgi db upgrade
    echo "      ✓ Migrationen angewendet"
else
    echo "      ⚠ Kein migrations/-Verzeichnis – übersprungen"
fi

# ---------------------------------------------------------------------------
# Node.js-Frontend
# ---------------------------------------------------------------------------
echo ""
echo "[3/4] Frontend-Abhängigkeiten installieren und bauen…"
cd "$FRONTEND_DIR"

if ! command -v node &>/dev/null; then
    echo "      ✗ node nicht gefunden – bitte Node.js >= 20 installieren"
    exit 1
fi

NODE_MAJOR=$(node -e "process.stdout.write(process.version.replace('v','').split('.')[0])")
if [ "$NODE_MAJOR" -lt 20 ]; then
    echo "      ✗ Node.js >= 20 erforderlich (gefunden: $(node --version))"
    exit 1
fi

npm install --silent
npm run build

echo "      ✓ Frontend gebaut → standdienst-api/static/dist/"

# ---------------------------------------------------------------------------
# Statische Verzeichnisse anlegen
# ---------------------------------------------------------------------------
echo ""
echo "[4/4] Verzeichnisse prüfen…"
cd "$API_DIR"

mkdir -p uploads logs static/dist

echo "      ✓ uploads/, logs/, static/dist/ vorhanden"

# ---------------------------------------------------------------------------
# Fertig
# ---------------------------------------------------------------------------
echo ""
echo "==> Installation abgeschlossen."
echo ""
echo "    Nächste Schritte:"
echo "    1. .env anlegen (SECRET_KEY, DATABASE_URL, ADMIN_PASSWORD)"
echo "    2. Flask-Migrationen: .venv/bin/flask --app wsgi db upgrade"
echo "    3. Starten:           gunicorn wsgi:app --config gunicorn.conf.py"
echo ""
