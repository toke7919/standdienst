#!/usr/bin/env bash
# Vollständiges Installations-Script für Standdienst v2 auf Debian/Ubuntu
# Verwendung: sudo bash install.sh [--dir /opt/standdienst]
set -euo pipefail

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
INSTALL_DIR="${1:-/opt/standdienst}"
SERVICE_USER="standdienst"
DB_NAME="standdienst"
DB_USER="standdienst"
REDIS_DB=0
APP_PORT=8420
DOMAIN="${DOMAIN:-localhost}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$REPO_ROOT/standdienst-api"
FRONTEND_DIR="$REPO_ROOT/standdienst-frontend"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
die()     { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }
section() { echo -e "\n${GREEN}━━━ $* ━━━${NC}"; }

require_root() { [ "$(id -u)" -eq 0 ] || die "Bitte als root ausführen: sudo bash install.sh"; }

# ---------------------------------------------------------------------------
# 0. Voraussetzungen prüfen
# ---------------------------------------------------------------------------
require_root
section "Standdienst v2 – Vollinstallation"
echo "  Zielverzeichnis : $INSTALL_DIR"
echo "  Service-User    : $SERVICE_USER"
echo "  Domain          : $DOMAIN"

# ---------------------------------------------------------------------------
# 1. Systempakete
# ---------------------------------------------------------------------------
section "1/7  Systempakete installieren"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    python3 python3-venv python3-dev \
    postgresql postgresql-contrib \
    redis-server \
    nodejs npm \
    git curl build-essential \
    libpq-dev \
    nginx \
    weasyprint \
    fonts-liberation fonts-dejavu

# Node.js >= 20 sicherstellen
NODE_MAJOR=$(node -e "process.stdout.write(process.version.replace('v','').split('.')[0])" 2>/dev/null || echo "0")
if [ "$NODE_MAJOR" -lt 20 ]; then
    warn "Node.js < 20 gefunden – installiere Node.js 20 LTS via NodeSource"
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - -s quiet
    apt-get install -y -qq nodejs
fi
info "Systempakete installiert (Node $(node --version), Python $(python3 --version))"

# ---------------------------------------------------------------------------
# 2. Service-User & Verzeichnisse
# ---------------------------------------------------------------------------
section "2/7  Service-User und Verzeichnisse"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
    info "Service-User '$SERVICE_USER' angelegt"
else
    info "Service-User '$SERVICE_USER' existiert bereits"
fi

mkdir -p "$INSTALL_DIR"/{uploads,logs,static/dist}
cp -r "$API_DIR"/. "$INSTALL_DIR/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
info "Verzeichnisse eingerichtet unter $INSTALL_DIR"

# ---------------------------------------------------------------------------
# 3. PostgreSQL einrichten
# ---------------------------------------------------------------------------
section "3/7  PostgreSQL konfigurieren"
systemctl enable --quiet postgresql
systemctl start postgresql

DB_PASSWORD="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)"

su -c "psql -c \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\" | grep -q 1 || \
    psql -c \"CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\"" postgres
su -c "psql -lqt | cut -d\| -f1 | grep -qw '$DB_NAME' || \
    psql -c \"CREATE DATABASE $DB_NAME OWNER $DB_USER;\"" postgres
su -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;\"" postgres

info "PostgreSQL: Datenbank '$DB_NAME' bereit"

# ---------------------------------------------------------------------------
# 4. Redis konfigurieren
# ---------------------------------------------------------------------------
section "4/7  Redis konfigurieren"
systemctl enable --quiet redis-server
systemctl start redis-server

# Maximal 256 MB, LRU-Eviction für Rate-Limiter-Keys
cat > /etc/redis/redis.conf.d/standdienst.conf 2>/dev/null || true
if [ -d /etc/redis/redis.conf.d ]; then
    cat > /etc/redis/redis.conf.d/standdienst.conf <<'EOF'
maxmemory 256mb
maxmemory-policy allkeys-lru
EOF
else
    sed -i 's/^# maxmemory .*/maxmemory 256mb/' /etc/redis/redis.conf
    sed -i 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
fi
systemctl restart redis-server
info "Redis konfiguriert und gestartet"

# ---------------------------------------------------------------------------
# 5. Python-Umgebung & Abhängigkeiten
# ---------------------------------------------------------------------------
section "5/7  Python-Abhängigkeiten installieren"
cd "$INSTALL_DIR"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
info "Python-Pakete installiert"

# ---------------------------------------------------------------------------
# 6. Secrets & .env
# ---------------------------------------------------------------------------
section "6/7  Konfiguration generieren"
SECRET_KEY="$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9+/=' | head -c 64)"
ADMIN_PW="$(openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | head -c 16)"
DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@127.0.0.1:5432/$DB_NAME"

ENV_FILE="$INSTALL_DIR/.env"
cat > "$ENV_FILE" <<EOF
# Standdienst v2 – Konfiguration
# Generiert am $(date '+%Y-%m-%d %H:%M:%S')

SECRET_KEY=$SECRET_KEY
ADMIN_PASSWORD=$ADMIN_PW
DATABASE_URL=$DATABASE_URL
RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/$REDIS_DB

APP_NAME=Standdienst
ADMIN_EMAIL=admin@$DOMAIN

# E-Mail (optional – kann auch über Admin-UI konfiguriert werden)
# MAIL_SERVER=smtp.example.com
# MAIL_PORT=587
# MAIL_USE_TLS=true
# MAIL_USERNAME=
# MAIL_PASSWORD=
# MAIL_FROM=noreply@$DOMAIN

SESSION_COOKIE_SECURE=true
FLASK_DEBUG=0
EOF
chmod 600 "$ENV_FILE"
chown "$SERVICE_USER:$SERVICE_USER" "$ENV_FILE"

info "Konfiguration geschrieben nach $ENV_FILE"
warn "Initiales Admin-Passwort: ${ADMIN_PW}"
warn "Bitte sofort nach dem ersten Login ändern!"

# ---------------------------------------------------------------------------
# Frontend bauen
# ---------------------------------------------------------------------------
cd "$FRONTEND_DIR"
npm install --silent
npm run build
info "Frontend gebaut → $INSTALL_DIR/static/dist/"

# ---------------------------------------------------------------------------
# Datenbankmigrationen
# ---------------------------------------------------------------------------
cd "$INSTALL_DIR"
FLASK_APP=wsgi DATABASE_URL="$DATABASE_URL" SECRET_KEY="$SECRET_KEY" \
    ADMIN_PASSWORD="$ADMIN_PW" \
    .venv/bin/flask db upgrade
info "Datenbankmigrationen angewendet"

# ---------------------------------------------------------------------------
# 7. systemd-Service
# ---------------------------------------------------------------------------
section "7/7  systemd-Service einrichten"
cat > /etc/systemd/system/standdienst.service <<EOF
[Unit]
Description=Standdienst v2 (Flask/Gunicorn)
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
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

# ---------------------------------------------------------------------------
# Nginx-Reverse-Proxy (optional)
# ---------------------------------------------------------------------------
if command -v nginx &>/dev/null; then
    cat > /etc/nginx/sites-available/standdienst <<EOF
server {
    listen 80;
    server_name $DOMAIN;

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
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF
    ln -sf /etc/nginx/sites-available/standdienst /etc/nginx/sites-enabled/standdienst
    rm -f /etc/nginx/sites-enabled/default
    nginx -t -q && systemctl reload nginx
    info "Nginx konfiguriert für $DOMAIN"
    warn "Für HTTPS: certbot --nginx -d $DOMAIN"
fi

# ---------------------------------------------------------------------------
# Zusammenfassung
# ---------------------------------------------------------------------------
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}  Standdienst v2 erfolgreich installiert!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  URL             : http://$DOMAIN"
echo "  Konfiguration   : $ENV_FILE"
echo "  App-Verzeichnis : $INSTALL_DIR"
echo "  Logs            : journalctl -u standdienst -f"
echo ""
echo -e "  ${YELLOW}Initiales Admin-Passwort: $ADMIN_PW${NC}"
echo "  → Bitte sofort nach erstem Login ändern!"
echo ""
echo "  Nächste Schritte:"
echo "  1. HTTPS einrichten:   certbot --nginx -d $DOMAIN"
echo "  2. E-Mail konfigurieren in der Admin-Oberfläche"
echo "  3. Erste Instanz anlegen unter http://$DOMAIN/api/admin/"
echo ""
