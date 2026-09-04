#!/usr/bin/env bash
# Update-Skript für die Docker-Compose-Installation von Standdienst.
# Lädt das neueste GitHub-Release, aktualisiert nur den Quellcode
# (nicht .env / docker-compose.override.yml), baut neu und startet neu.
#
# Im Installationsverzeichnis ausführen:
#   cd /pfad/zur/installation && sudo bash update-docker.sh [--check] [--yes]
#   --check   Nur prüfen, ob ein Update verfügbar ist – nichts verändern
#   --yes     Keine Rückfragen, direkt anwenden
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "  ${GREEN}✓${NC} $*"; }
warn()    { echo -e "  ${YELLOW}!${NC} $*"; }
die()     { echo -e "  ${RED}✗${NC} $*" >&2; exit 1; }
section() { echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }
ask()     { printf "  ${CYAN}?${NC} $* "; }

require_root() { [ "$(id -u)" -eq 0 ] || die "Bitte als root ausführen: sudo bash update-docker.sh"; }

# ---------------------------------------------------------------------------
# Argumente parsen
# ---------------------------------------------------------------------------
CHECK_ONLY=false
ASSUME_YES=false

for arg in "$@"; do
    case "$arg" in
        --check) CHECK_ONLY=true ;;
        --yes|-y) ASSUME_YES=true ;;
        *) die "Unbekannte Option: $arg – das Skript arbeitet immer im aktuellen Verzeichnis, kein Pfad-Argument." ;;
    esac
done

require_root

# Immer das aktuelle Verzeichnis. Bitte vorher ins Installationsverzeichnis wechseln.
INSTALL_DIR="$(pwd)"

_wrong_dir_hint="bitte ins Standdienst-Installationsverzeichnis wechseln (cd /pfad/zur/installation) und erneut ausführen"
[ -f "$INSTALL_DIR/.env" ] || die ".env nicht gefunden – $_wrong_dir_hint."
[ -f "$INSTALL_DIR/docker-compose.yml" ] || die "docker-compose.yml nicht gefunden – $_wrong_dir_hint."
[ -f "$INSTALL_DIR/standdienst-api/version.py" ] || die "standdienst-api/version.py nicht gefunden – $_wrong_dir_hint."

# shellcheck source=/dev/null
set -o allexport; source "$INSTALL_DIR/.env"; set +o allexport

# Fest hinterlegtes Upstream-Repo aus version.py (Single Source of Truth).
GITHUB_REPO="$(python3 -c "
ns={}
exec(open('$INSTALL_DIR/standdienst-api/version.py').read(), ns)
print(ns.get('GITHUB_REPO',''))
" 2>/dev/null || true)"
[ -n "$GITHUB_REPO" ] || die "GITHUB_REPO fehlt in $INSTALL_DIR/standdienst-api/version.py – Installation unvollständig."

# ---------------------------------------------------------------------------
# Einmalige Migration: benannte Volumes -> ./data/ (Bind-Mounts)
# ---------------------------------------------------------------------------
# Ältere Installationen nutzten benannte Docker-Volumes (<projekt>_pgdata usw.).
# Diese Funktion übernimmt deren Inhalt einmalig nach ./data/, sobald die neue
# docker-compose.yml (mit Bind-Mounts) in Kraft ist. Postgres bleibt auf der
# gleichen Major-Version, daher ist die rohe Kopie des Datenverzeichnisses sicher.
_migrate_named_volumes() {
    # Schon migriert? (./data/postgres nicht leer)
    [ -z "$(ls -A "$INSTALL_DIR/data/postgres" 2>/dev/null || true)" ] || return 0

    local proj
    proj="${COMPOSE_PROJECT_NAME:-$(basename "$INSTALL_DIR" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]//g')}"
    if ! docker volume inspect "${proj}_pgdata" >/dev/null 2>&1; then
        # Fallback: genau ein *_pgdata-Volume auf dem Host?
        if [ "$(docker volume ls --format '{{.Name}}' | grep -cE '_pgdata$' || true)" = "1" ]; then
            proj="$(docker volume ls --format '{{.Name}}' | grep -E '_pgdata$' | sed 's/_pgdata$//')"
        else
            return 0   # nichts zu migrieren
        fi
    fi
    docker volume inspect "${proj}_pgdata" >/dev/null 2>&1 || return 0

    section "Einmalige Datenmigration: benannte Volumes → ./data/"
    warn "Gefunden: Volume-Satz '${proj}_*' – Inhalt wird nach ./data/ übernommen."

    docker compose down 2>/dev/null || true
    mkdir -p "$INSTALL_DIR"/data/postgres "$INSTALL_DIR"/data/redis \
             "$INSTALL_DIR"/data/uploads "$INSTALL_DIR"/data/logs "$INSTALL_DIR"/data/backups

    _copy_volume() {  # $1 = Volume-Suffix, $2 = Zielordner unter data/
        local vol="${proj}_$1"
        docker volume inspect "$vol" >/dev/null 2>&1 || return 0
        if docker run --rm -v "$vol:/from:ro" -v "$INSTALL_DIR/data/$2:/to" alpine:3 \
               sh -c 'cp -a /from/. /to/'; then
            info "  $vol → data/$2"
        else
            die "Kopie von $vol nach data/$2 fehlgeschlagen – Update abgebrochen, Daten unverändert."
        fi
    }
    # Redis (nur Rate-Limit-Cache + ALTCHA-Replay) wird bewusst nicht übernommen.
    _copy_volume pgdata  postgres
    _copy_volume uploads uploads
    _copy_volume logs    logs
    _copy_volume backups backups
    chmod 700 "$INSTALL_DIR/data/postgres" 2>/dev/null || true

    info "Migration abgeschlossen. Die alten Volumes bleiben vorerst erhalten."
    info "Nach erfolgreichem Start entfernbar mit:"
    info "  docker volume rm ${proj}_pgdata ${proj}_redisdata ${proj}_uploads ${proj}_logs ${proj}_backups"
}

# ---------------------------------------------------------------------------
# Versions-Hilfsfunktionen
# ---------------------------------------------------------------------------
_current_version() {
    python3 -c "
ns={}
exec(open('$INSTALL_DIR/standdienst-api/version.py').read(), ns)
print(ns.get('VERSION','unbekannt'))
" 2>/dev/null || echo "unbekannt"
}

_is_newer() {
    python3 -c "
import sys
a=tuple(int(x) for x in sys.argv[1].lstrip('v').split('-')[0].split('.'))
b=tuple(int(x) for x in sys.argv[2].lstrip('v').split('-')[0].split('.'))
exit(0 if a > b else 1)
" "$1" "$2" 2>/dev/null
}

# ---------------------------------------------------------------------------
# GitHub-Release-Handling (identisch zu install-docker.sh)
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
# Banner
# ---------------------------------------------------------------------------
clear
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Standdienst – Docker-Update             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ---------------------------------------------------------------------------
# Versionsvergleich
# ---------------------------------------------------------------------------
section "Versionen prüfen"
CURRENT="$(_current_version)"
info "Installierte Version: $CURRENT"

RELEASE_JSON="$(_latest_release)"
LATEST="$(echo "$RELEASE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name',''))" 2>/dev/null || true)"
TARBALL_URL="$(echo "$RELEASE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tarball_url',''))" 2>/dev/null || true)"

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
        ask "Trotzdem fortfahren und neu bauen? [j/N]:"
        read -r answer
        [[ "${answer:-n}" =~ ^[JjYy]$ ]] || { echo "  Abgebrochen."; exit 0; }
    fi
else
    echo ""
    echo -e "  ${YELLOW}Update verfügbar:${NC} $CURRENT → $LATEST"
    echo ""
    echo "$RELEASE_JSON" | python3 -c "
import sys,json
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

cd "$INSTALL_DIR"

# ---------------------------------------------------------------------------
# Backup erstellen
# ---------------------------------------------------------------------------
section "Backup erstellen"
BACKUP_LABEL="vor_update_${LATEST//\//_}"
if BACKUP_OUT="$(docker compose exec -T -e BACKUP_LABEL="$BACKUP_LABEL" api python3 - <<PYEOF 2>&1
import os
from wsgi import app
with app.app_context():
    from app.api.admin.backup import run_backup
    try:
        print(run_backup(label=os.environ['BACKUP_LABEL']))
    except Exception as e:
        print(f'FEHLER: {e}')
        raise SystemExit(1)
PYEOF
)"; then
    info "Backup erstellt: $BACKUP_OUT"
else
    warn "Backup fehlgeschlagen (kein Passwort gesetzt?) – Update wird trotzdem fortgesetzt: $BACKUP_OUT"
fi

# ---------------------------------------------------------------------------
# Release herunterladen und entpacken
# ---------------------------------------------------------------------------
section "Release herunterladen"
TMPDIR_UPDATE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_UPDATE"' EXIT
curl -fsSL -o "$TMPDIR_UPDATE/release.tar.gz" "$TARBALL_URL"
tar -xzf "$TMPDIR_UPDATE/release.tar.gz" -C "$TMPDIR_UPDATE"
EXTRACTED="$(find "$TMPDIR_UPDATE" -mindepth 1 -maxdepth 1 -type d | head -1)"
[ -n "$EXTRACTED" ] || die "Entpacken fehlgeschlagen"
info "Entpackt: $(basename "$EXTRACTED")"

# ---------------------------------------------------------------------------
# Dateien synchronisieren (.env und docker-compose.override.yml bleiben unangetastet)
# ---------------------------------------------------------------------------
section "Dateien aktualisieren"
if ! command -v rsync &>/dev/null; then
    warn "rsync nicht gefunden – wird installiert"
    apt-get update -qq && apt-get install -y -qq rsync
fi
# rsync betrifft nur standdienst-api/ und standdienst-frontend/. ./data/ (Bind-Mounts
# für Datenbank, Uploads, Backups, Logs), .env und docker-compose.override.yml
# liegen daneben und werden nie angefasst.
rsync -a --delete "$EXTRACTED/standdienst-api/" "$INSTALL_DIR/standdienst-api/"
rsync -a --delete "$EXTRACTED/standdienst-frontend/" "$INSTALL_DIR/standdienst-frontend/"
cp "$EXTRACTED/docker-compose.yml" "$INSTALL_DIR/docker-compose.yml"
info "Quellcode aktualisiert (.env, docker-compose.override.yml und data/ unangetastet)"

# ---------------------------------------------------------------------------
# Datenmigration (nur beim ersten Update nach der Umstellung auf ./data/)
# ---------------------------------------------------------------------------
_migrate_named_volumes

# ---------------------------------------------------------------------------
# Container neu bauen und starten
# ---------------------------------------------------------------------------
section "Container neu bauen und starten"
mkdir -p "$INSTALL_DIR"/data/postgres "$INSTALL_DIR"/data/redis \
         "$INSTALL_DIR"/data/uploads "$INSTALL_DIR"/data/logs "$INSTALL_DIR"/data/backups
docker compose build
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
    die "Anwendung antwortet nach 30s nicht – bitte 'docker compose logs api -n 50' und 'docker compose logs frontend -n 50' prüfen"
fi

# ---------------------------------------------------------------------------
# Fertig
# ---------------------------------------------------------------------------
NEW_VERSION="$(_current_version)"
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Docker-Update abgeschlossen!            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Version  : $CURRENT → $NEW_VERSION"
echo "  Logs     : docker compose -f ${INSTALL_DIR}/docker-compose.yml logs -f api"
echo ""
