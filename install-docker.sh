#!/usr/bin/env bash
# Eigenständiger Docker-Compose-Installer für Standdienst.
# Lädt das neueste GitHub-Release, installiert Docker falls nötig,
# generiert Secrets automatisch und startet den Stack.
# Verwendung: sudo bash install-docker.sh [Installationspfad]
set -euo pipefail

# ---------------------------------------------------------------------------
# Konfiguration & Defaults
# ---------------------------------------------------------------------------
DEFAULT_INSTALL_DIR="/opt/standdienst-docker"
DEFAULT_PORT=80
# Bootstrap-Repo: hier noch hartkodiert, weil der Code (und damit
# standdienst-api/version.py als Single Source of Truth) erst nach dem Download
# lokal vorliegt. Muss mit GITHUB_REPO in version.py übereinstimmen.
GITHUB_REPO="toke7919/standdienst"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "  ${GREEN}✓${NC} $*"; }
warn()    { echo -e "  ${YELLOW}!${NC} $*"; }
die()     { echo -e "  ${RED}✗${NC} $*" >&2; exit 1; }
section() { echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }
ask()     { echo -e "  ${CYAN}?${NC} $*"; }

require_root() { [ "$(id -u)" -eq 0 ] || die "Bitte als root ausführen: sudo bash install-docker.sh"; }

# ---------------------------------------------------------------------------
# GitHub-Release-Handling (DNS-Fallback wie in update.sh)
# ---------------------------------------------------------------------------
_resolve_github_api_ip() {
    local ip
    ip=$(getent hosts api.github.com 2>/dev/null | awk '{print $1; exit}') && [ -n "$ip" ] && echo "$ip" && return
    ip=$(dig +short +time=3 +tries=1 @8.8.8.8 api.github.com 2>/dev/null | grep -E '^[0-9]+\.[0-9]+' | head -1) && [ -n "$ip" ] && echo "$ip" && return
    ip=$(nslookup api.github.com 8.8.8.8 2>/dev/null | awk '/^Address:/{ip=$2} END{print ip}' | grep -E '^[0-9]+\.[0-9]+') && [ -n "$ip" ] && echo "$ip" && return
    return 1
}

_github_get() {
    local url="$1"
    # Öffentliches Repo – keine Authentifizierung nötig.
    local args=(-fsSL -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" --connect-timeout 10)

    if curl "${args[@]}" "$url" 2>/dev/null; then
        return 0
    fi

    local ip
    if ip=$(_resolve_github_api_ip 2>/dev/null) && [ -n "$ip" ]; then
        warn "System-DNS für api.github.com fehlgeschlagen – Fallback via 8.8.8.8 ($ip)"
        curl "${args[@]}" --resolve "api.github.com:443:$ip" "$url"
        return $?
    fi

    return 1
}

_latest_release() {
    local json
    json="$(_github_get "https://api.github.com/repos/${GITHUB_REPO}/releases/latest" 2>&1)" \
        || die "GitHub-API nicht erreichbar (GITHUB_REPO=$GITHUB_REPO)."
    echo "$json"
}

# ---------------------------------------------------------------------------
# 0. Voraussetzungen
# ---------------------------------------------------------------------------
require_root
clear
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Standdienst – Docker-Installation       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ---------------------------------------------------------------------------
# 1. Docker Engine + Compose-Plugin
# ---------------------------------------------------------------------------
section "1/6  Docker prüfen"
if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    info "Docker vorhanden ($(docker --version))"
else
    warn "Docker nicht gefunden – installiere via get.docker.com"
    curl -fsSL https://get.docker.com | sh
    systemctl enable --quiet docker
    systemctl start docker
    info "Docker installiert ($(docker --version))"
fi

# ---------------------------------------------------------------------------
# 2. Konfiguration abfragen
# ---------------------------------------------------------------------------
section "2/6  Konfiguration"

if [ -n "${1:-}" ]; then
    INSTALL_DIR="$1"
else
    ask "Installationspfad [${DEFAULT_INSTALL_DIR}]:"
    read -r INSTALL_DIR
    INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
fi
INSTALL_DIR="${INSTALL_DIR%/}"

while true; do
    ask "Web-Port [${DEFAULT_PORT}]:"
    read -r FRONTEND_PORT
    FRONTEND_PORT="${FRONTEND_PORT:-$DEFAULT_PORT}"

    if ! [[ "$FRONTEND_PORT" =~ ^[0-9]+$ ]]; then
        warn "Ungültige Eingabe – bitte eine Portnummer eingeben."
        continue
    fi

    if [ "$FRONTEND_PORT" -lt 1 ] || [ "$FRONTEND_PORT" -gt 65535 ]; then
        warn "Port muss zwischen 1 und 65535 liegen."
        continue
    fi

    if command -v ss &>/dev/null; then
        PORT_IN_USE=$(ss -tlnp 2>/dev/null | grep -c ":${FRONTEND_PORT} " || true)
    elif command -v netstat &>/dev/null; then
        PORT_IN_USE=$(netstat -tlnp 2>/dev/null | grep -c ":${FRONTEND_PORT} " || true)
    else
        PORT_IN_USE=0
        warn "ss/netstat nicht gefunden – Port-Prüfung übersprungen"
    fi

    if [ "$PORT_IN_USE" -gt 0 ]; then
        warn "Port ${FRONTEND_PORT} ist bereits belegt. Bitte einen anderen Port wählen."
        continue
    fi

    info "Port ${FRONTEND_PORT} ist verfügbar"
    break
done

SERVER_IP="$(hostname -I | awk '{print $1}')"
ask "Öffentliche URL (für E-Mail-Links & CORS) [http://${SERVER_IP}]:"
read -r FRONTEND_URL
FRONTEND_URL="${FRONTEND_URL:-http://${SERVER_IP}}"
FRONTEND_URL="${FRONTEND_URL%/}"

echo ""
echo "  Installationspfad : ${INSTALL_DIR}"
echo "  Web-Port          : ${FRONTEND_PORT}"
echo "  Öffentliche URL   : ${FRONTEND_URL}"
echo ""
ask "Installation starten? [J/n]:"
read -r CONFIRM
CONFIRM="${CONFIRM:-J}"
[[ "$CONFIRM" =~ ^[JjYy]$ ]] || { echo "Abgebrochen."; exit 0; }

# ---------------------------------------------------------------------------
# 3. Release herunterladen
# ---------------------------------------------------------------------------
section "3/6  Release herunterladen"
RELEASE_JSON="$(_latest_release)"
LATEST_TAG="$(echo "$RELEASE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name',''))" 2>/dev/null || true)"
TARBALL_URL="$(echo "$RELEASE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tarball_url',''))" 2>/dev/null || true)"
[ -n "$LATEST_TAG" ] || die "Konnte kein Release finden (GITHUB_REPO=$GITHUB_REPO)"
info "Neuestes Release: $LATEST_TAG"

TMPDIR_INSTALL="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_INSTALL"' EXIT
curl -fsSL -o "$TMPDIR_INSTALL/release.tar.gz" "$TARBALL_URL"
tar -xzf "$TMPDIR_INSTALL/release.tar.gz" -C "$TMPDIR_INSTALL"
EXTRACTED="$(find "$TMPDIR_INSTALL" -mindepth 1 -maxdepth 1 -type d | head -1)"
[ -n "$EXTRACTED" ] || die "Entpacken fehlgeschlagen"
info "Entpackt: $(basename "$EXTRACTED")"

mkdir -p "$INSTALL_DIR"
if ! command -v rsync &>/dev/null; then
    warn "rsync nicht gefunden – wird installiert"
    apt-get update -qq && apt-get install -y -qq rsync
fi
rsync -a --delete "$EXTRACTED/standdienst-api/" "$INSTALL_DIR/standdienst-api/"
rsync -a --delete "$EXTRACTED/standdienst-frontend/" "$INSTALL_DIR/standdienst-frontend/"
cp "$EXTRACTED/docker-compose.yml" "$INSTALL_DIR/docker-compose.yml"
cp "$EXTRACTED/update-docker.sh" "$INSTALL_DIR/update-docker.sh"
chmod +x "$INSTALL_DIR/update-docker.sh"
info "Quellcode nach $INSTALL_DIR kopiert"

# ---------------------------------------------------------------------------
# 4. Konfiguration schreiben
# ---------------------------------------------------------------------------
section "4/6  Konfiguration schreiben"
ENV_FILE="$INSTALL_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    info ".env existiert bereits – wird nicht überschrieben"
else
    SECRET_KEY="$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9+/=' | head -c 64)"
    POSTGRES_PASSWORD="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)"
    SESSION_COOKIE_SECURE=false
    [[ "$FRONTEND_URL" == https://* ]] && SESSION_COOKIE_SECURE=true

    cat > "$ENV_FILE" <<EOF
# Standdienst – Docker-Compose-Konfiguration
# Generiert am $(date '+%Y-%m-%d %H:%M:%S') von install-docker.sh

SECRET_KEY=$SECRET_KEY
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
FRONTEND_URL=$FRONTEND_URL
FRONTEND_PORT=$FRONTEND_PORT
SESSION_COOKIE_SECURE=$SESSION_COOKIE_SECURE
COMPOSE_FILE=docker-compose.yml:docker-compose.override.yml
EOF
    chmod 600 "$ENV_FILE"
    info "Konfigurationsdatei geschrieben: $ENV_FILE"
fi

OVERRIDE_FILE="$INSTALL_DIR/docker-compose.override.yml"
if [ -f "$OVERRIDE_FILE" ]; then
    info "docker-compose.override.yml existiert bereits – wird nicht überschrieben"
else
    cat > "$OVERRIDE_FILE" <<'EOF'
# Lokale Anpassungen an der Docker-Compose-Konfiguration.
# Diese Datei wird von update-docker.sh NIE überschrieben oder gelöscht.
#
# Beispiel: zusätzlichen Host-Port für den Frontend-Container freigeben
#
# services:
#   frontend:
#     ports:
#       - "8080:80"
EOF
    info "Override-Datei angelegt: $OVERRIDE_FILE"
fi

# ---------------------------------------------------------------------------
# 5. Container bauen
# ---------------------------------------------------------------------------
section "5/6  Container bauen"
cd "$INSTALL_DIR"
docker compose build
info "Images gebaut"

# ---------------------------------------------------------------------------
# 6. Container starten
# ---------------------------------------------------------------------------
section "6/6  Container starten"
docker compose up -d

info "Warte auf Bereitschaft (bis zu 30s)..."
READY=false
for i in $(seq 1 30); do
    if curl -fsS -o /dev/null "http://localhost:${FRONTEND_PORT}/api/setup/status" 2>/dev/null; then
        READY=true
        break
    fi
    sleep 1
done

if [ "$READY" = true ]; then
    info "Anwendung ist erreichbar (http://localhost:${FRONTEND_PORT}/api/setup/status)"
else
    die "Anwendung antwortet nach 30s nicht – bitte 'docker compose logs api' und 'docker compose logs frontend' prüfen"
fi

# ---------------------------------------------------------------------------
# Fertig
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Docker-Installation abgeschlossen!      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Installationspfad : ${INSTALL_DIR}"
echo "  Erreichbar unter  : ${FRONTEND_URL}"
echo "  Konfiguration     : ${INSTALL_DIR}/.env"
echo "  Lokale Anpassungen: ${INSTALL_DIR}/docker-compose.override.yml"
echo "  Logs              : docker compose -f ${INSTALL_DIR}/docker-compose.yml logs -f"
echo ""
echo -e "  ${YELLOW}Nächster Schritt:${NC}"
echo -e "  Öffne ${CYAN}${FRONTEND_URL}/setup${NC} im Browser und"
echo "  schließe die Erstkonfiguration ab."
echo ""
