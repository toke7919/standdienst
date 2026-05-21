#!/usr/bin/env bash
# Standdienst – Backup-Script
# Erstellt ein verschlüsseltes pg_dump-Backup (AES-256-GCM + HMAC-SHA-256).
# Kompatibel mit restore.sh; für Serverwechsel muss der gleiche SECRET_KEY verwendet werden.
#
# Verwendung: ./backup.sh [--dir /pfad/zu/standdienst]
#   --dir   Installationsverzeichnis (Standard: Verzeichnis dieses Scripts)
#
# Backups werden automatisch rotiert; maximal 20 .pgdump.enc-Dateien werden behalten.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dir) INSTALL_DIR="$2"; shift 2 ;;
        *) echo "Unbekannte Option: $1" >&2; exit 1 ;;
    esac
done

ENV_FILE="${INSTALL_DIR}/.env"
[[ -f "${ENV_FILE}" ]] || { echo "Fehler: .env nicht gefunden: ${ENV_FILE}" >&2; exit 1; }

set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

# BACKUP_DIR aus .env oder Standard; relative Pfade werden relativ zu standdienst-api aufgelöst
_BACKUP_DIR_RAW="${BACKUP_DIR:-backups}"
if [[ "${_BACKUP_DIR_RAW}" == /* ]]; then
    BACKUP_DIR="${_BACKUP_DIR_RAW}"
else
    BACKUP_DIR="${INSTALL_DIR}/${_BACKUP_DIR_RAW}"
fi

PYTHON="${INSTALL_DIR}/.venv/bin/python3"

[[ -x "${PYTHON}" ]]        || { echo "Fehler: Python-Venv nicht gefunden: ${PYTHON}" >&2; exit 1; }
[[ -n "${SECRET_KEY:-}" ]]  || { echo "Fehler: SECRET_KEY fehlt in .env" >&2; exit 1; }
[[ -n "${DATABASE_URL:-}" ]] || { echo "Fehler: DATABASE_URL fehlt in .env" >&2; exit 1; }
command -v pg_dump >/dev/null || { echo "Fehler: pg_dump nicht gefunden (postgresql-client installieren)" >&2; exit 1; }
command -v gzip    >/dev/null || { echo "Fehler: gzip nicht gefunden" >&2; exit 1; }

# Datenbankverbindung aus DATABASE_URL parsen
PG_PARSE="$("${PYTHON}" -c "
from urllib.parse import urlparse, unquote
import os
u = urlparse(os.environ['DATABASE_URL'])
print(u.hostname or 'localhost')
print(u.port or 5432)
print(unquote(u.username or ''))
print(unquote(u.password or ''))
print(u.path.lstrip('/'))
")"
PG_HOST="$(echo "${PG_PARSE}" | sed -n '1p')"
PG_PORT="$(echo "${PG_PARSE}" | sed -n '2p')"
PG_USER="$(echo "${PG_PARSE}" | sed -n '3p')"
PG_PASS="$(echo "${PG_PARSE}" | sed -n '4p')"
PG_DB="$(echo "${PG_PARSE}"   | sed -n '5p')"

mkdir -p "${BACKUP_DIR}"

TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
OUTFILE="${BACKUP_DIR}/standdienst_${TIMESTAMP}.pgdump.enc"

echo "Erstelle Backup für Datenbank '${PG_DB}' auf ${PG_HOST}:${PG_PORT} ..."

# Temp-Script für Verschlüsselung
ENCRYPT_SCRIPT="$(mktemp /tmp/sd_encrypt_XXXXX.py)"
trap 'rm -f "${ENCRYPT_SCRIPT}"' EXIT

cat > "${ENCRYPT_SCRIPT}" << 'PYEOF'
import sys, os, hashlib, hmac as hmac_mod
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

data = sys.stdin.buffer.read()
key = hashlib.sha256(os.environ['SECRET_KEY'].encode()).digest()

# HMAC-Signatur voranstellen
magic = b'SDHMAC'
sig = hmac_mod.new(key, data, hashlib.sha256).digest()
signed = magic + sig + data

# AES-256-GCM verschlüsseln
aesgcm = AESGCM(key)
nonce = os.urandom(12)
ct = aesgcm.encrypt(nonce, signed, None)
sys.stdout.buffer.write(nonce + ct)
PYEOF

PGPASSWORD="${PG_PASS}" pg_dump \
    -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
    --format=plain \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    | gzip \
    | "${PYTHON}" "${ENCRYPT_SCRIPT}" \
    > "${OUTFILE}"

SIZE="$(du -sh "${OUTFILE}" | cut -f1)"
echo "Backup gespeichert: $(basename "${OUTFILE}") (${SIZE})"

# Auto-Rotation: älteste Backups löschen wenn mehr als MAX_BACKUPS vorhanden
MAX_BACKUPS=20
mapfile -t ALL_BACKUPS < <(ls -t "${BACKUP_DIR}"/standdienst_*.pgdump.enc 2>/dev/null || true)
if [[ ${#ALL_BACKUPS[@]} -gt ${MAX_BACKUPS} ]]; then
    EXCESS=$(( ${#ALL_BACKUPS[@]} - MAX_BACKUPS ))
    for F in "${ALL_BACKUPS[@]: -${EXCESS}}"; do
        echo "Rotiere: $(basename "${F}")"
        rm -f "${F}"
    done
fi

TOTAL="$(ls "${BACKUP_DIR}"/standdienst_*.pgdump.enc 2>/dev/null | wc -l)"
echo "Fertig. Backups gesamt: ${TOTAL}"
