#!/usr/bin/env bash
# Update-Skript für Standdienst
# Holt das neueste GitHub-Release, erstellt ein Backup, baut das Frontend und startet den Dienst neu.
# Verwendung: sudo bash update.sh [--check] [--yes] [Installationspfad]
#   --check   Nur prüfen, ob ein Update verfügbar ist – nichts verändern
#   --yes     Keine Rückfragen, direkt anwenden
set -euo pipefail

# ---------------------------------------------------------------------------
# Farben & Hilfsfunktionen
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "  ${GREEN}✓${NC} $*"; }
warn()    { echo -e "  ${YELLOW}!${NC} $*"; }
die()     { echo -e "  ${RED}✗${NC} $*" >&2; exit 1; }
section() { echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }
ask()     { printf "  ${CYAN}?${NC} $* "; }

require_root() { [ "$(id -u)" -eq 0 ] || die "Bitte als root ausführen: sudo bash update.sh"; }

# ---------------------------------------------------------------------------
# Argumente parsen
# ---------------------------------------------------------------------------
CHECK_ONLY=false
ASSUME_YES=false
INSTALL_DIR=""

for arg in "$@"; do
    case "$arg" in
        --check) CHECK_ONLY=true ;;
        --yes|-y) ASSUME_YES=true ;;
        -*) die "Unbekannte Option: $arg" ;;
        *) INSTALL_DIR="$arg" ;;
    esac
done

require_root

INSTALL_DIR="${INSTALL_DIR:-/opt/standdienst}"
INSTALL_DIR="${INSTALL_DIR%/}"
SERVICE_USER="standdienst"
DB_NAME="standdienst"

[ -d "$INSTALL_DIR" ] || die "Installationsverzeichnis nicht gefunden: $INSTALL_DIR"
[ -f "$INSTALL_DIR/.env" ] || die ".env nicht gefunden: $INSTALL_DIR/.env"
[ -f "$INSTALL_DIR/version.py" ] || die "version.py nicht gefunden – kein gültiges Standdienst-Verzeichnis"

# ---------------------------------------------------------------------------
# Konfiguration aus .env laden
# ---------------------------------------------------------------------------
# shellcheck source=/dev/null
set -o allexport; source "$INSTALL_DIR/.env"; set +o allexport

GITHUB_REPO="${GITHUB_REPO:-}"
DATABASE_URL="${DATABASE_URL:-}"

# ---------------------------------------------------------------------------
# Versions-Hilfsfunktionen
# ---------------------------------------------------------------------------
_current_version() {
    python3 -c "
ns={}
exec(open('$INSTALL_DIR/version.py').read(), ns)
print(ns.get('VERSION','unbekannt'))
" 2>/dev/null || echo "unbekannt"
}

_vtag() {
    local v="$1"
    [[ "$v" == v* ]] && echo "$v" || echo "v$v"
}

_is_newer() {
    # Gibt 0 (wahr) zurück wenn $1 neuer als $2 ist
    python3 -c "
a=tuple(int(x) for x in '$1'.lstrip('v').split('-')[0].split('.'))
b=tuple(int(x) for x in '$2'.lstrip('v').split('-')[0].split('.'))
exit(0 if a > b else 1)
" 2>/dev/null
}

# ---------------------------------------------------------------------------
# GitHub-API-Abfrage (mit DNS-Fallback über 8.8.8.8)
# ---------------------------------------------------------------------------

# Löst api.github.com auf; bei Ausfall des System-DNS wird 8.8.8.8 verwendet.
_resolve_github_api_ip() {
    local ip
    # 1. Systemresolver (schnell, meist ausreichend)
    ip=$(getent hosts api.github.com 2>/dev/null | awk '{print $1; exit}') && [ -n "$ip" ] && echo "$ip" && return
    # 2. Externer DNS via dig
    ip=$(dig +short +time=3 +tries=1 @8.8.8.8 api.github.com 2>/dev/null | grep -E '^[0-9]+\.[0-9]+' | head -1) && [ -n "$ip" ] && echo "$ip" && return
    # 3. Externer DNS via nslookup
    ip=$(nslookup api.github.com 8.8.8.8 2>/dev/null | awk '/^Address:/{ip=$2} END{print ip}' | grep -E '^[0-9]+\.[0-9]+') && [ -n "$ip" ] && echo "$ip" && return
    return 1
}

_github_get() {
    local url="$1"
    local pat="${GITHUB_PAT:-}"
    local args=(-fsSL -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" --connect-timeout 10)
    [[ -n "$pat" ]] && args+=(-H "Authorization: Bearer $pat")

    # Erst normaler Versuch
    if curl "${args[@]}" "$url" 2>/dev/null; then
        return 0
    fi

    # DNS-Fallback: IP über externen Resolver ermitteln
    local ip
    if ip=$(_resolve_github_api_ip 2>/dev/null) && [ -n "$ip" ]; then
        warn "System-DNS für api.github.com fehlgeschlagen – Fallback via 8.8.8.8 ($ip)"
        curl "${args[@]}" --resolve "api.github.com:443:$ip" "$url"
        return $?
    fi

    return 1
}

_latest_release() {
    if [ -z "${GITHUB_REPO:-}" ]; then
        die "GITHUB_REPO ist nicht in $INSTALL_DIR/.env gesetzt.
  Bitte eintragen: echo 'GITHUB_REPO=toke7919/standdienst' >> $INSTALL_DIR/.env"
    fi
    local json
    json="$(_github_get "https://api.github.com/repos/${GITHUB_REPO}/releases/latest" 2>&1)" \
        || die "GitHub-API nicht erreichbar (GITHUB_REPO=$GITHUB_REPO).
  Prüfen: curl -fsSL https://api.github.com/repos/${GITHUB_REPO}/releases/latest
  DNS-Fix (falls Auflösung scheitert): echo '$(dig +short @8.8.8.8 api.github.com | head -1) api.github.com' >> /etc/hosts"
    echo "$json"
}

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
clear
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Standdienst – Update                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ---------------------------------------------------------------------------
# Versionsvergleich
# ---------------------------------------------------------------------------
section "Versionen prüfen"
CURRENT="$(_current_version)"
info "Installierte Version: $CURRENT"

RELEASE_JSON="$(_latest_release)"

LATEST="$(echo "$RELEASE_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tag_name',''))" 2>/dev/null || true)"
TARBALL_URL="$(echo "$RELEASE_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tarball_url',''))" 2>/dev/null || true)"

if [ -z "$LATEST" ]; then
    echo -e "  ${RED}✗${NC} GitHub-Antwort:" >&2
    echo "$RELEASE_JSON" | head -5 >&2
    die "Konnte Tag-Name nicht aus GitHub-Antwort lesen (GITHUB_REPO=$GITHUB_REPO)"
fi

info "Verfügbares Release : $LATEST"

if ! _is_newer "$LATEST" "$CURRENT"; then
    echo ""
    info "Bereits auf dem aktuellen Stand. Kein Update nötig."
    $CHECK_ONLY && exit 0
    if ! $ASSUME_YES; then
        ask "Trotzdem fortfahren und neu installieren? [j/N]:"
        read -r answer
        [[ "${answer:-n}" =~ ^[JjYy]$ ]] || { echo "  Abgebrochen."; exit 0; }
    fi
else
    echo ""
    echo -e "  ${YELLOW}Update verfügbar:${NC} $CURRENT → $LATEST"
    echo ""
    echo "$RELEASE_JSON" | python3 -c "
import sys,json,textwrap
d=json.load(sys.stdin)
notes=d.get('body','').strip()
if notes:
    print('  Release-Notes:')
    for line in notes.splitlines()[:20]:
        print('  ' + line)
" 2>/dev/null || true
    echo ""
fi

$CHECK_ONLY && exit 0

if ! $ASSUME_YES; then
    ask "Update jetzt anwenden? [J/n]:"
    read -r answer
    answer="${answer:-J}"
    [[ "$answer" =~ ^[JjYy]$ ]] || { echo "  Abgebrochen."; exit 0; }
fi

# ---------------------------------------------------------------------------
# Backup erstellen (.sdbackup via Python-Backend)
# ---------------------------------------------------------------------------
section "Backup erstellen"
PYTHON="${INSTALL_DIR}/.venv/bin/python3"
if [ -x "${PYTHON}" ]; then
    BACKUP_LABEL="vor_update_${LATEST//\//_}"
    BACKUP_OUT="$("${PYTHON}" - <<PYEOF 2>&1
import sys, os
os.chdir('${INSTALL_DIR}')
sys.path.insert(0, '${INSTALL_DIR}')
from wsgi import app
with app.app_context():
    from app.api.admin.backup import run_backup
    try:
        name = run_backup(label='${BACKUP_LABEL}')
        print(name)
    except Exception as e:
        print(f'FEHLER: {e}', file=sys.stderr)
        sys.exit(1)
PYEOF
    )"
    if [ $? -eq 0 ] && [ -n "$BACKUP_OUT" ]; then
        chown "$SERVICE_USER:$SERVICE_USER" "${INSTALL_DIR}/backups/${BACKUP_OUT}" 2>/dev/null || true
        info "Backup erstellt: ${BACKUP_OUT}"
    else
        warn "Backup fehlgeschlagen (kein Passwort gesetzt?) – Update wird trotzdem fortgesetzt"
    fi
else
    warn "Python-Venv nicht gefunden – Backup übersprungen"
fi

# ---------------------------------------------------------------------------
# Release herunterladen und entpacken
# ---------------------------------------------------------------------------
section "Release herunterladen"
TMPDIR_UPDATE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_UPDATE"' EXIT

TAR_PATH="$TMPDIR_UPDATE/release.tar.gz"
GITHUB_PAT="${GITHUB_PAT:-}"
curl -fsSL \
    ${GITHUB_PAT:+-H "Authorization: Bearer $GITHUB_PAT"} \
    -o "$TAR_PATH" \
    "$TARBALL_URL"
info "Heruntergeladen: $LATEST"

tar -xzf "$TAR_PATH" -C "$TMPDIR_UPDATE"
EXTRACTED="$(find "$TMPDIR_UPDATE" -mindepth 1 -maxdepth 1 -type d | head -1)"
[ -n "$EXTRACTED" ] || die "Entpacken fehlgeschlagen"
info "Entpackt: $(basename "$EXTRACTED")"

# ---------------------------------------------------------------------------
# Frontend bauen (aus dem neuen Quellcode)
# ---------------------------------------------------------------------------
section "Frontend bauen"
SRC_FRONTEND="$EXTRACTED/standdienst-frontend"
if [ -d "$SRC_FRONTEND" ] && command -v npm &>/dev/null; then
    npm install --silent --prefix "$SRC_FRONTEND"
    npm run build --prefix "$SRC_FRONTEND"
    info "Frontend gebaut → static/dist/"
else
    warn "Frontend nicht gebaut (npm oder standdienst-frontend/ nicht gefunden)"
fi

# ---------------------------------------------------------------------------
# API-Dateien kopieren (ohne .env, uploads, backups, logs, .venv)
# ---------------------------------------------------------------------------
section "Dateien aktualisieren"
SRC_API="$EXTRACTED/standdienst-api"
[ -d "$SRC_API" ] || die "standdienst-api/ nicht im Release-Tarball enthalten"

if ! command -v rsync &>/dev/null; then
    warn "rsync nicht gefunden – wird installiert"
    apt-get install -y -qq rsync
fi

rsync -a --delete \
    --exclude='.env' \
    --exclude='uploads/' \
    --exclude='backups/' \
    --exclude='logs/' \
    --exclude='.venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='instance/' \
    "$SRC_API/" "$INSTALL_DIR/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
info "API-Dateien aktualisiert"

# ---------------------------------------------------------------------------
# Python-Abhängigkeiten installieren
# ---------------------------------------------------------------------------
section "Python-Abhängigkeiten"
"$INSTALL_DIR/.venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"
info "pip install abgeschlossen"

# ---------------------------------------------------------------------------
# Datenbankmigrationen
# ---------------------------------------------------------------------------
section "Datenbankmigrationen"
su -s /bin/bash "$SERVICE_USER" -c \
    "cd '$INSTALL_DIR' && FLASK_APP=wsgi '$INSTALL_DIR/.venv/bin/flask' db upgrade" \
    2>&1 | sed 's/^/  /'
info "Migrationen angewendet"

# ---------------------------------------------------------------------------
# Dienst neu starten
# ---------------------------------------------------------------------------
section "Dienst neu starten"
systemctl restart standdienst
sleep 2
if systemctl is-active --quiet standdienst; then
    info "standdienst.service läuft"
else
    die "standdienst.service konnte nicht gestartet werden – bitte 'journalctl -u standdienst -n 50' prüfen"
fi

# ---------------------------------------------------------------------------
# Fertig
# ---------------------------------------------------------------------------
NEW_VERSION="$(_current_version)"
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Update abgeschlossen!                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Version  : $CURRENT → $NEW_VERSION"
echo "  Logs     : journalctl -u standdienst -f"
echo ""
