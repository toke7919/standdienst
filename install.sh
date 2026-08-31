#!/usr/bin/env bash
# Technische Installation von Standdienst auf Debian/Ubuntu
# Die Erstkonfiguration erfolgt anschließend über das Web-Setup-Interface.
# Verwendung: sudo bash install.sh [Installationspfad]
set -euo pipefail

# ---------------------------------------------------------------------------
# Konfiguration & Defaults
# ---------------------------------------------------------------------------
DEFAULT_INSTALL_DIR="/opt/standdienst"
DEFAULT_PORT=8420
SERVICE_USER="standdienst"
DB_NAME="standdienst"
DB_USER="standdienst"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$REPO_ROOT/standdienst-api"
FRONTEND_DIR="$REPO_ROOT/standdienst-frontend"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "  ${GREEN}✓${NC} $*"; }
warn()    { echo -e "  ${YELLOW}!${NC} $*"; }
die()     { echo -e "  ${RED}✗${NC} $*" >&2; exit 1; }
section() { echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }
ask()     { echo -e "  ${CYAN}?${NC} $*"; }

require_root() { [ "$(id -u)" -eq 0 ] || die "Bitte als root ausführen: sudo bash install.sh"; }

# ---------------------------------------------------------------------------
# 0. Voraussetzungen
# ---------------------------------------------------------------------------
require_root
clear
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Standdienst – Installation              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Technische Installation. Die Erstkonfiguration"
echo "  (Admin-Account, Mail, URL) erfolgt danach über"
echo "  das Web-Setup-Interface."
echo ""

# ---------------------------------------------------------------------------
# Installationspfad abfragen
# ---------------------------------------------------------------------------
if [ -n "${1:-}" ]; then
    INSTALL_DIR="$1"
else
    ask "Installationspfad [${DEFAULT_INSTALL_DIR}]:"
    read -r INSTALL_DIR
    INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
fi
INSTALL_DIR="${INSTALL_DIR%/}"

# ---------------------------------------------------------------------------
# Port abfragen und prüfen
# ---------------------------------------------------------------------------
section "Port-Konfiguration"
while true; do
    ask "Anwendungs-Port [${DEFAULT_PORT}]:"
    read -r APP_PORT
    APP_PORT="${APP_PORT:-$DEFAULT_PORT}"

    # Nur Zahlen erlaubt
    if ! [[ "$APP_PORT" =~ ^[0-9]+$ ]]; then
        warn "Ungültige Eingabe – bitte eine Portnummer eingeben."
        continue
    fi

    # Bereich prüfen
    if [ "$APP_PORT" -lt 1024 ] || [ "$APP_PORT" -gt 65535 ]; then
        warn "Port muss zwischen 1024 und 65535 liegen."
        continue
    fi

    # Verfügbarkeit prüfen (ss bevorzugt, Fallback auf netstat)
    if command -v ss &>/dev/null; then
        PORT_IN_USE=$(ss -tlnp 2>/dev/null | grep -c ":${APP_PORT} " || true)
    elif command -v netstat &>/dev/null; then
        PORT_IN_USE=$(netstat -tlnp 2>/dev/null | grep -c ":${APP_PORT} " || true)
    else
        PORT_IN_USE=0
        warn "ss/netstat nicht gefunden – Port-Prüfung übersprungen"
    fi

    if [ "$PORT_IN_USE" -gt 0 ]; then
        warn "Port ${APP_PORT} ist bereits belegt. Bitte einen anderen Port wählen."
        continue
    fi

    info "Port ${APP_PORT} ist verfügbar"
    break
done

# Zusammenfassung anzeigen und bestätigen
echo ""
echo "  Installationspfad : ${INSTALL_DIR}"
echo "  Service-User      : ${SERVICE_USER}"
echo "  Anwendungs-Port   : ${APP_PORT}"
echo ""
ask "Installation starten? [J/n]:"
read -r CONFIRM
CONFIRM="${CONFIRM:-J}"
[[ "$CONFIRM" =~ ^[JjYy]$ ]] || { echo "Abgebrochen."; exit 0; }

# ---------------------------------------------------------------------------
# 1. Systempakete
# ---------------------------------------------------------------------------
section "1/6  Systempakete installieren"
export DEBIAN_FRONTEND=noninteractive

# Defekte Drittanbieter-Repositories entfernen, die apt-get update blockieren würden
# (packages.sury.org/python existiert nicht mehr)
if find /etc/apt/sources.list.d/ -name "*.list" -print0 2>/dev/null | \
        xargs -0 grep -l "sury.org/python" 2>/dev/null | grep -q .; then
    find /etc/apt/sources.list.d/ -name "*.list" -print0 | \
        xargs -0 grep -l "sury.org/python" | xargs rm -f
    warn "Veraltetes packages.sury.org/python-Repository entfernt"
fi

apt-get update -qq
apt-get install -y -qq \
    python3 python3-venv python3-dev \
    postgresql postgresql-contrib \
    redis-server \
    git curl build-essential \
    libpq-dev \
    nginx \
    weasyprint \
    fonts-liberation fonts-dejavu

# Node.js >= 20
NODE_MAJOR=$(node -e "process.stdout.write(process.version.replace('v','').split('.')[0])" 2>/dev/null || echo "0")
if [ "$NODE_MAJOR" -lt 20 ]; then
    warn "Node.js < 20 gefunden – installiere Node.js 20 LTS via NodeSource"
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -s -- -y
    apt-get install -y -qq nodejs
fi
info "Systempakete installiert (Node $(node --version), Python $(python3 --version))"

# ---------------------------------------------------------------------------
# 2. Service-User & Verzeichnisse
# ---------------------------------------------------------------------------
section "2/6  Service-User und Verzeichnisse"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
    info "Service-User '$SERVICE_USER' angelegt"
else
    info "Service-User '$SERVICE_USER' existiert bereits"
fi

mkdir -p "$INSTALL_DIR"
cp -r "$API_DIR"/. "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR"/{uploads,logs,static/dist}
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
info "Dateien nach $INSTALL_DIR kopiert"

# ---------------------------------------------------------------------------
# 3. PostgreSQL & Redis
# ---------------------------------------------------------------------------
section "3/6  Datenbank und Cache einrichten"
systemctl enable --quiet postgresql
systemctl start postgresql

DB_PASSWORD="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)"

# User anlegen oder Passwort aktualisieren (Reininstallation auf gleichem System)
PG_USER_EXISTS="$(su -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\"" postgres)"
if [ "$PG_USER_EXISTS" = "1" ]; then
    su -c "psql -c \"ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\"" postgres
    info "PostgreSQL: Passwort für User '$DB_USER' aktualisiert"
else
    su -c "psql -c \"CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\"" postgres
    info "PostgreSQL: User '$DB_USER' angelegt"
fi
su -c "psql -lqt | cut -d\| -f1 | grep -qw '$DB_NAME' || \
    psql -c \"CREATE DATABASE $DB_NAME OWNER $DB_USER;\"" postgres
su -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;\"" postgres
info "PostgreSQL: Datenbank '$DB_NAME' bereit"

systemctl enable --quiet redis-server
systemctl start redis-server
info "Redis gestartet"

# ---------------------------------------------------------------------------
# 4. Python-Umgebung + Abhängigkeiten
# ---------------------------------------------------------------------------
section "4/6  Python-Abhängigkeiten installieren"
cd "$INSTALL_DIR"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
info "Python-Pakete installiert"

# Minimale .env erzeugen (nur technische Variablen – kein Admin-Passwort)
SECRET_KEY="$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9+/=' | head -c 64)"
DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@127.0.0.1:5432/$DB_NAME"

# GitHub-Repository aus Git-Remote ableiten (ermöglicht automatische Updates)
GITHUB_REPO_LINE=""
GITHUB_REMOTE="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
if [[ "$GITHUB_REMOTE" =~ github\.com[:/]([^/]+/[^/]+) ]]; then
    GITHUB_SLUG="${BASH_REMATCH[1]%.git}"   # .git-Suffix entfernen
    GITHUB_REPO_LINE="GITHUB_REPO=${GITHUB_SLUG}"
    info "GitHub-Repository erkannt: ${GITHUB_SLUG}"
fi

cat > "$INSTALL_DIR/.env" <<EOF
# Standdienst – technische Konfiguration
# Ersteinrichtung (Admin, Mail, URL) erfolgt über das Web-Setup-Interface.
# Generiert am $(date '+%Y-%m-%d %H:%M:%S')

SECRET_KEY=$SECRET_KEY
DATABASE_URL=$DATABASE_URL
RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0
GUNICORN_BIND=127.0.0.1:${APP_PORT}
SESSION_COOKIE_SECURE=true
FLASK_DEBUG=0
EOF
[ -n "$GITHUB_REPO_LINE" ] && echo "$GITHUB_REPO_LINE" >> "$INSTALL_DIR/.env"
chmod 600 "$INSTALL_DIR/.env"
chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"
info "Konfigurationsdatei geschrieben: $INSTALL_DIR/.env"

# Datenbankmigrationen (als Service-User damit logs/ nicht root-owned wird)
su -s /bin/bash "$SERVICE_USER" -c \
    "FLASK_APP=wsgi DATABASE_URL='$DATABASE_URL' SECRET_KEY='$SECRET_KEY' '$INSTALL_DIR/.venv/bin/flask' db upgrade"
info "Datenbankmigrationen angewendet"

# Eigentümer nach Migration sicherstellen (falls doch root-Dateien entstanden)
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"/{logs,uploads}

# ---------------------------------------------------------------------------
# 5. Frontend bauen
# ---------------------------------------------------------------------------
section "5/6  Frontend bauen"
cd "$FRONTEND_DIR"
npm install --silent
npm run build
info "Frontend gebaut → $INSTALL_DIR/static/dist/"

# ---------------------------------------------------------------------------
# 6. systemd + Nginx
# ---------------------------------------------------------------------------
section "6/6  Dienste einrichten"

# systemd-Service
cat > /etc/systemd/system/standdienst.service <<EOF
[Unit]
Description=Standdienst (Flask/Gunicorn)
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
Environment=HOME=$INSTALL_DIR
ExecStart=$INSTALL_DIR/.venv/bin/gunicorn wsgi:app --config gunicorn.conf.py
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=30
Restart=always
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=standdienst

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --quiet standdienst
systemctl restart standdienst
info "standdienst.service aktiviert und gestartet"

# Scheduler-Service (separater Prozess, läuft Jobs genau einmal)
sed "s|INSTALL_DIR_PLACEHOLDER|$INSTALL_DIR|g" \
    "$API_DIR/standdienst-scheduler.service" \
    > /etc/systemd/system/standdienst-scheduler.service
systemctl daemon-reload
systemctl enable --quiet standdienst-scheduler
systemctl restart standdienst-scheduler
info "standdienst-scheduler.service aktiviert und gestartet"

# Sudoers: Service-User darf beide Dienste ohne Passwort neu starten
SYSTEMCTL_PATH="$(command -v systemctl)"
printf '%s ALL=(ALL) NOPASSWD: %s restart standdienst, %s restart standdienst-scheduler\n' \
    "$SERVICE_USER" "$SYSTEMCTL_PATH" "$SYSTEMCTL_PATH" \
    > /etc/sudoers.d/standdienst-restart
chmod 440 /etc/sudoers.d/standdienst-restart
info "Sudoers-Eintrag angelegt (${SYSTEMCTL_PATH})"

# Nginx
cat > /etc/nginx/sites-available/standdienst <<EOF
server {
    listen 80 default_server;
    server_name _;

    client_max_body_size 20M;

    location /static/ {
        alias $INSTALL_DIR/static/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location /uploads/ {
        alias $INSTALL_DIR/uploads/;
        expires 1d;
    }

    location / {
        # Scheme-Normalisierung: X-Forwarded-Proto aus vorgelagertem Proxy ermitteln.
        # Priorität: X-Forwarded-Ssl: on > X-Forwarded-Proto > \$scheme (eigene Verbindung).
        # X-Forwarded-Ssl und X-Forwarded-Protocol werden danach gelöscht, damit Gunicorn
        # nur einen einzigen, konsistenten Scheme-Header sieht (kein "Contradictory scheme headers").
        set \$proto \$scheme;
        if (\$http_x_forwarded_proto) {
            set \$proto \$http_x_forwarded_proto;
        }
        if (\$http_x_forwarded_ssl = "on") {
            set \$proto https;
        }
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Forwarded "";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$proto;
        proxy_set_header X-Forwarded-Ssl "";
        proxy_set_header X-Forwarded-Protocol "";
        proxy_read_timeout 120s;
    }
}
EOF
ln -sf /etc/nginx/sites-available/standdienst /etc/nginx/sites-enabled/standdienst
rm -f /etc/nginx/sites-enabled/default
nginx -t -q && systemctl reload nginx
info "Nginx konfiguriert (Port 80 → ${APP_PORT})"

# ---------------------------------------------------------------------------
# Fertig
# ---------------------------------------------------------------------------
SERVER_IP="$(hostname -I | awk '{print $1}')"
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Installation abgeschlossen!             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  App läuft intern auf Port : ${APP_PORT}"
echo "  Nginx-Proxy               : Port 80"
echo "  Erreichbar unter          : http://${SERVER_IP}"
echo "  Logs (API)                : journalctl -u standdienst -f"
echo "  Logs (Scheduler)          : journalctl -u standdienst-scheduler -f"
echo ""
echo -e "  ${YELLOW}Nächster Schritt:${NC}"
echo -e "  Öffne ${CYAN}http://${SERVER_IP}/setup${NC} im Browser und"
echo "  schließe die Erstkonfiguration ab:"
echo "  • Admin-Account anlegen"
echo "  • Basis-URL konfigurieren"
echo "  • Mail-Server einrichten (optional)"
echo "  • GitHub-Token für Updates (optional)"
echo ""
echo "  Für HTTPS: certbot --nginx -d <domain>"
echo ""
