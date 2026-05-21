#!/usr/bin/env bash
# Standdienst – Restore-Script
# Stellt ein verschlüsseltes pg_dump-Backup interaktiv wieder her.
# Für Serverwechsel: Backup-Datei auf den neuen Server kopieren, gleichen SECRET_KEY
# in .env eintragen und dieses Script ausführen.
#
# Verwendung: ./restore.sh [--dir /pfad/zu/standdienst]
#   --dir   Installationsverzeichnis (Standard: Verzeichnis dieses Scripts)
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

_BACKUP_DIR_RAW="${BACKUP_DIR:-backups}"
if [[ "${_BACKUP_DIR_RAW}" == /* ]]; then
    BACKUP_DIR="${_BACKUP_DIR_RAW}"
else
    BACKUP_DIR="${INSTALL_DIR}/${_BACKUP_DIR_RAW}"
fi

PYTHON="${INSTALL_DIR}/.venv/bin/python3"

[[ -x "${PYTHON}" ]]         || { echo "Fehler: Python-Venv nicht gefunden: ${PYTHON}" >&2; exit 1; }
[[ -n "${SECRET_KEY:-}" ]]   || { echo "Fehler: SECRET_KEY fehlt in .env" >&2; exit 1; }
[[ -n "${DATABASE_URL:-}" ]] || { echo "Fehler: DATABASE_URL fehlt in .env" >&2; exit 1; }
command -v psql   >/dev/null || { echo "Fehler: psql nicht gefunden (postgresql-client installieren)" >&2; exit 1; }
command -v gunzip >/dev/null || { echo "Fehler: gunzip nicht gefunden" >&2; exit 1; }

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

# Backups auflisten (neueste zuerst)
mapfile -t BACKUP_FILES < <(ls -t "${BACKUP_DIR}"/standdienst_*.pgdump.enc 2>/dev/null || true)

if [[ ${#BACKUP_FILES[@]} -eq 0 ]]; then
    echo ""
    echo "Keine Backups gefunden in: ${BACKUP_DIR}"
    echo "Backups werden mit ./backup.sh erstellt."
    exit 1
fi

echo ""
echo "Standdienst – Backup-Wiederherstellung"
echo "═══════════════════════════════════════════════════════════════════"
printf "  %-4s  %-22s  %-8s  %s\n" "Nr." "Datum (UTC)" "Größe" "Dateiname"
echo "───────────────────────────────────────────────────────────────────"

for i in "${!BACKUP_FILES[@]}"; do
    FILE="${BACKUP_FILES[$i]}"
    NAME="$(basename "${FILE}")"
    SIZE="$(du -sh "${FILE}" | cut -f1)"
    # Zeitstempel aus Dateiname: standdienst_YYYYMMDD_HHMMSS.pgdump.enc
    if [[ "${NAME}" =~ _([0-9]{8})_([0-9]{6})\.pgdump\.enc$ ]]; then
        D="${BASH_REMATCH[1]}"
        T="${BASH_REMATCH[2]}"
        DISPLAY="${D:6:2}.${D:4:2}.${D:0:4}  ${T:0:2}:${T:2:2}:${T:4:2}"
    else
        DISPLAY="$(date -r "${FILE}" "+%d.%m.%Y  %H:%M:%S" 2>/dev/null || echo '–')"
    fi
    printf "  %-4s  %-22s  %-8s  %s\n" "$((i+1))." "${DISPLAY}" "${SIZE}" "${NAME}"
done

echo "═══════════════════════════════════════════════════════════════════"
echo ""
read -rp "  Backup-Nummer eingeben (oder 'q' zum Abbrechen): " SELECTION

if [[ "${SELECTION}" == "q" || "${SELECTION}" == "Q" ]]; then
    echo "Abgebrochen."
    exit 0
fi

if ! [[ "${SELECTION}" =~ ^[0-9]+$ ]] || \
   [[ ${SELECTION} -lt 1 ]] || \
   [[ ${SELECTION} -gt ${#BACKUP_FILES[@]} ]]; then
    echo "Ungültige Auswahl." >&2
    exit 1
fi

SELECTED="${BACKUP_FILES[$((SELECTION-1))]}"
SELECTED_NAME="$(basename "${SELECTED}")"

echo ""
echo "  ╔════════════════════════════════════════════════════════════╗"
echo "  ║  ACHTUNG – Dieser Vorgang kann nicht rückgängig gemacht   ║"
echo "  ║  werden! Der gesamte aktuelle Datenbankinhalt wird        ║"
echo "  ║  gelöscht und durch das gewählte Backup ersetzt.          ║"
echo "  ╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  Backup:    ${SELECTED_NAME}"
echo "  Datenbank: ${PG_DB} auf ${PG_HOST}:${PG_PORT}"
echo ""
read -rp "  Zur Bestätigung 'ja' eingeben: " CONFIRM

if [[ "${CONFIRM}" != "ja" ]]; then
    echo "Abgebrochen."
    exit 0
fi

echo ""
echo "Entschlüssele und prüfe Backup ..."

# Temp-Script für Entschlüsselung
DECRYPT_SCRIPT="$(mktemp /tmp/sd_decrypt_XXXXX.py)"
trap 'rm -f "${DECRYPT_SCRIPT}"' EXIT

cat > "${DECRYPT_SCRIPT}" << 'PYEOF'
import sys, os, hashlib, hmac as hmac_mod
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

data = sys.stdin.buffer.read()
key = hashlib.sha256(os.environ['SECRET_KEY'].encode()).digest()

# Entschlüsseln
nonce, ct = data[:12], data[12:]
aesgcm = AESGCM(key)
try:
    signed = aesgcm.decrypt(nonce, ct, None)
except Exception as e:
    sys.stderr.write(f'Entschlüsselung fehlgeschlagen: {e}\n')
    sys.stderr.write('Hinweis: Wurde das Backup mit demselben SECRET_KEY erstellt?\n')
    sys.exit(1)

# HMAC-Signatur prüfen
magic = b'SDHMAC'
if signed.startswith(magic):
    offset = len(magic)
    sig_stored = signed[offset:offset + 32]
    payload = signed[offset + 32:]
    sig_expected = hmac_mod.new(key, payload, hashlib.sha256).digest()
    if not hmac_mod.compare_digest(sig_stored, sig_expected):
        sys.stderr.write('Backup-Signatur ungültig – Backup möglicherweise manipuliert!\n')
        sys.exit(2)
    sys.stdout.buffer.write(payload)
else:
    sys.stderr.write('Hinweis: Backup ohne HMAC-Signatur (altes Format)\n')
    sys.stdout.buffer.write(signed)
PYEOF

echo "Stelle Datenbank '${PG_DB}' wieder her ..."

cat "${SELECTED}" \
    | "${PYTHON}" "${DECRYPT_SCRIPT}" \
    | gunzip \
    | PGPASSWORD="${PG_PASS}" psql \
        -h "${PG_HOST}" \
        -p "${PG_PORT}" \
        -U "${PG_USER}" \
        -d "${PG_DB}" \
        -q \
        -v ON_ERROR_STOP=1

echo ""
echo "Backup erfolgreich wiederhergestellt!"
echo "Dienst neu starten: systemctl restart standdienst"
