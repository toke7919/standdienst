#!/usr/bin/env bash
# Vollständige Deinstallation von Standdienst v2
# Verwendung: sudo bash uninstall.sh [Installationspfad]
set -euo pipefail

DEFAULT_INSTALL_DIR="/opt/standdienst"
SERVICE_USER="standdienst"
DB_NAME="standdienst"
DB_USER="standdienst"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "  ${GREEN}✓${NC} $*"; }
warn()    { echo -e "  ${YELLOW}!${NC} $*"; }
skip()    { echo -e "  ${CYAN}–${NC} $* (übersprungen)"; }
section() { echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }
ask()     { printf "  ${CYAN}?${NC} $* "; }

require_root() { [ "$(id -u)" -eq 0 ] || { echo -e "${RED}Bitte als root ausführen: sudo bash uninstall.sh${NC}" >&2; exit 1; }; }

yesno() {
    local default="${2:-n}"
    ask "$1 [j/N]:"
    read -r answer
    answer="${answer:-$default}"
    [[ "$answer" =~ ^[JjYy]$ ]]
}

require_root

# Installationspfad bestimmen
INSTALL_DIR="${1:-}"
if [ -z "$INSTALL_DIR" ]; then
    ask "Installationspfad [${DEFAULT_INSTALL_DIR}]:"
    read -r INSTALL_DIR
    INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
fi
INSTALL_DIR="${INSTALL_DIR%/}"

clear
echo ""
echo -e "${RED}╔══════════════════════════════════════════════╗${NC}"
echo -e "${RED}║      Standdienst v2 – Deinstallation        ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Installationspfad : ${INSTALL_DIR}"
echo "  Service-User      : ${SERVICE_USER}"
echo ""
echo -e "  ${RED}WARNUNG:${NC} Diese Aktion löscht die Anwendung."
echo "  Daten können nicht wiederhergestellt werden."
echo ""

yesno "Deinstallation wirklich durchführen?" || { echo "  Abgebrochen."; exit 0; }

# ---------------------------------------------------------------------------
# 1. systemd-Service stoppen und entfernen
# ---------------------------------------------------------------------------
section "1/5  systemd-Service entfernen"
if systemctl is-active --quiet standdienst 2>/dev/null; then
    systemctl stop standdienst
    info "standdienst.service gestoppt"
else
    skip "standdienst.service war nicht aktiv"
fi

if systemctl is-enabled --quiet standdienst 2>/dev/null; then
    systemctl disable standdienst
    info "standdienst.service deaktiviert"
fi

if [ -f /etc/systemd/system/standdienst.service ]; then
    rm -f /etc/systemd/system/standdienst.service
    systemctl daemon-reload
    info "standdienst.service entfernt"
else
    skip "standdienst.service war nicht vorhanden"
fi

# ---------------------------------------------------------------------------
# 2. Nginx-Konfiguration entfernen
# ---------------------------------------------------------------------------
section "2/5  Nginx-Konfiguration entfernen"
NGINX_REMOVED=0
if [ -f /etc/nginx/sites-enabled/standdienst ]; then
    rm -f /etc/nginx/sites-enabled/standdienst
    NGINX_REMOVED=1
fi
if [ -f /etc/nginx/sites-available/standdienst ]; then
    rm -f /etc/nginx/sites-available/standdienst
    NGINX_REMOVED=1
fi
if [ "$NGINX_REMOVED" -eq 1 ]; then
    nginx -t -q 2>/dev/null && systemctl reload nginx 2>/dev/null || true
    info "Nginx-Konfiguration entfernt und neu geladen"
else
    skip "Keine Nginx-Konfiguration gefunden"
fi

# ---------------------------------------------------------------------------
# 3. Installationsverzeichnis löschen
# ---------------------------------------------------------------------------
section "3/5  Installationsverzeichnis löschen"
if [ -d "$INSTALL_DIR" ]; then
    echo ""
    echo -e "  ${YELLOW}Das Verzeichnis enthält alle Anwendungsdaten:${NC}"
    echo "  • Python-Venv (.venv/)"
    echo "  • Hochgeladene Dateien (uploads/)"
    echo "  • Logs (logs/)"
    echo "  • Konfiguration (.env)"
    echo ""
    if yesno "Verzeichnis '$INSTALL_DIR' vollständig löschen?"; then
        rm -rf "$INSTALL_DIR"
        info "Verzeichnis $INSTALL_DIR gelöscht"
    else
        skip "Installationsverzeichnis beibehalten"
    fi
else
    skip "Verzeichnis $INSTALL_DIR nicht gefunden"
fi

# ---------------------------------------------------------------------------
# 4. PostgreSQL-Datenbank und -Benutzer löschen
# ---------------------------------------------------------------------------
section "4/5  PostgreSQL aufräumen"
if command -v psql &>/dev/null && systemctl is-active --quiet postgresql 2>/dev/null; then
    echo ""
    echo -e "  ${YELLOW}Datenbank '$DB_NAME' und Benutzer '$DB_USER' löschen?${NC}"
    echo "  (Alle Standdienst-Daten gehen verloren!)"
    echo ""
    if yesno "PostgreSQL-Datenbank '$DB_NAME' löschen?"; then
        su -c "psql -c \"DROP DATABASE IF EXISTS $DB_NAME;\"" postgres 2>/dev/null && \
            info "Datenbank '$DB_NAME' gelöscht" || warn "Datenbank konnte nicht gelöscht werden"
        su -c "psql -c \"DROP USER IF EXISTS $DB_USER;\"" postgres 2>/dev/null && \
            info "DB-Benutzer '$DB_USER' gelöscht" || warn "Benutzer konnte nicht gelöscht werden"
    else
        skip "PostgreSQL-Datenbank beibehalten"
    fi
else
    skip "PostgreSQL nicht aktiv oder nicht installiert"
fi

# ---------------------------------------------------------------------------
# 5. Service-User löschen
# ---------------------------------------------------------------------------
section "5/5  Service-User entfernen"
if id "$SERVICE_USER" &>/dev/null; then
    if yesno "System-User '$SERVICE_USER' löschen?"; then
        userdel "$SERVICE_USER" 2>/dev/null && info "User '$SERVICE_USER' gelöscht" \
            || warn "User konnte nicht gelöscht werden"
    else
        skip "System-User beibehalten"
    fi
else
    skip "System-User '$SERVICE_USER' nicht vorhanden"
fi

# ---------------------------------------------------------------------------
# Optionale System-Pakete entfernen
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}━━━ Optionale Bereinigung ━━━${NC}"
echo ""
echo "  Installierte System-Pakete (PostgreSQL, Redis, Nginx, Node.js)"
echo "  werden nur entfernt wenn du sie für NICHTS ANDERES verwendest."
echo ""
if yesno "System-Pakete deinstallieren (PostgreSQL, Redis, Node.js)?"; then
    apt-get remove -y -qq postgresql redis-server nodejs nginx 2>/dev/null || true
    apt-get autoremove -y -qq 2>/dev/null || true
    info "Pakete entfernt"
else
    skip "System-Pakete beibehalten"
fi

# ---------------------------------------------------------------------------
# Fertig
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Deinstallation abgeschlossen.           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Standdienst v2 wurde entfernt."
echo ""
echo "  Nicht automatisch bereinigt (manuell prüfen):"
echo "  • Redis-Konfiguration: /etc/redis/redis.conf"
echo "  • Zertifikate (Let's Encrypt): certbot delete"
echo "  • Fail2Ban-Regeln (falls konfiguriert)"
echo ""
