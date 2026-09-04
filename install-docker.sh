#!/usr/bin/env bash
# Docker-Compose-Installer für Standdienst.
#
# Wird IM Projektverzeichnis ausgeführt:
#   git clone https://github.com/toke7919/standdienst.git
#   cd standdienst
#   sudo bash install-docker.sh
#
# Installiert Docker (falls nötig), generiert Secrets automatisch und startet
# den Stack an Ort und Stelle. Kein Kopieren nach /opt, keine Pfad-Abfrage.
set -euo pipefail

DEFAULT_PORT=80

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "  ${GREEN}✓${NC} $*"; }
warn()    { echo -e "  ${YELLOW}!${NC} $*"; }
die()     { echo -e "  ${RED}✗${NC} $*" >&2; exit 1; }
section() { echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }
ask()     { echo -e "  ${CYAN}?${NC} $*"; }

require_root() { [ "$(id -u)" -eq 0 ] || die "Bitte als root ausführen: sudo bash install-docker.sh"; }

# ---------------------------------------------------------------------------
# Docker CE aus dem offiziellen Docker-apt-Repo (Debian/Ubuntu)
# ---------------------------------------------------------------------------
_install_docker_apt() {
    command -v apt-get &>/dev/null || die \
        "Automatische Docker-Installation nur auf Debian/Ubuntu (apt). Docker bitte manuell installieren: https://docs.docker.com/engine/install/"

    local distro codename
    distro="$(. /etc/os-release && echo "${ID:-}")"
    codename="$(. /etc/os-release && echo "${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}")"
    case "$distro" in
        debian|ubuntu) ;;
        *) die "Distribution '$distro' nicht unterstützt – Docker bitte manuell installieren: https://docs.docker.com/engine/install/" ;;
    esac
    [ -n "$codename" ] || die "Konnte die Release-Codebezeichnung nicht ermitteln (/etc/os-release)."

    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL "https://download.docker.com/linux/${distro}/gpg" -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc https://download.docker.com/linux/${distro} ${codename} stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --quiet --now docker
}

# ---------------------------------------------------------------------------
# 0. Voraussetzungen
# ---------------------------------------------------------------------------
require_root

INSTALL_DIR="$(pwd)"
{ [ -d "$INSTALL_DIR/standdienst-api" ] && [ -d "$INSTALL_DIR/standdienst-frontend" ] \
  && [ -f "$INSTALL_DIR/docker-compose.yml" ]; } || die \
  "Bitte im Projektverzeichnis ausführen (git clone … && cd standdienst && sudo bash install-docker.sh).
    Erwartet im aktuellen Verzeichnis: standdienst-api/, standdienst-frontend/, docker-compose.yml"

clear
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Standdienst – Docker-Installation       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ---------------------------------------------------------------------------
# 1. Docker Engine + Compose-Plugin
# ---------------------------------------------------------------------------
section "1/4  Docker prüfen"
if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    info "Docker vorhanden ($(docker --version))"
else
    warn "Docker nicht gefunden – installiere Docker CE aus dem offiziellen Docker-apt-Repo"
    _install_docker_apt
    info "Docker installiert ($(docker --version))"
fi

# ---------------------------------------------------------------------------
# 2. Konfiguration abfragen
# ---------------------------------------------------------------------------
section "2/4  Konfiguration"

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
# 3. Konfiguration schreiben
# ---------------------------------------------------------------------------
section "3/4  Konfiguration schreiben"
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
# 4. Container bauen und starten
# ---------------------------------------------------------------------------
section "4/4  Container bauen und starten"
cd "$INSTALL_DIR"
docker compose build
info "Images gebaut"
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
echo "  Update            : cd ${INSTALL_DIR} && sudo bash update-docker.sh"
echo "  Logs              : docker compose logs -f"
echo ""
echo -e "  ${YELLOW}Nächster Schritt:${NC}"
echo -e "  Öffne ${CYAN}${FRONTEND_URL}/setup${NC} im Browser und"
echo "  schließe die Erstkonfiguration ab."
echo ""
