# Docker-Compose-Installer für Standdienst — Design-Spec

**Datum:** 2026-08-31
**Ansatz:** Eigenständiger Release-Installer (analog `update.sh`), unabhängig vom Git-Checkout
**Scope:** 2 neue Shell-Scripts (`install-docker.sh`, `update-docker.sh`) + kleine Korrektur an `docker-compose.yml`

---

## Ziel

Vollautomatische Installation und Aktualisierung von Standdienst per Docker Compose auf einem frischen Debian/Ubuntu-Server, analog zu den bestehenden Bare-Metal-Scripts `install.sh`/`update.sh`:

- Benötigte Programme (Docker Engine, Compose-Plugin) werden automatisch installiert.
- Sicherheitsschlüssel (`SECRET_KEY`, `POSTGRES_PASSWORD`) werden automatisch generiert.
- Web-Port ist anpassbar. Die API bleibt bewusst intern-only (kein Host-Port), keine separate Portabfrage nötig.
- Werte, die nicht automatisch ermittelbar sind (Installationspfad, Web-Port, öffentliche URL), werden interaktiv abgefragt.
- Manuelle Anpassungen an der Docker-Compose-Konfiguration überleben Updates, über den nativen `docker-compose.override.yml`-Mechanismus.
- `.env` enthält `COMPOSE_FILE`, sodass `docker compose up -d` im Installationsverzeichnis ohne weitere Flags funktioniert.

## Nicht-Ziele (YAGNI)

- Kein `uninstall-docker.sh`.
- Kein Diff/Merge für Änderungen an `docker-compose.yml` — die Override-Datei deckt Anpassungsbedarf ab.
- Kein `docker image prune` nach dem Update.
- Keine Unterstützung für andere Distributionen als Debian/Ubuntu.
- Keine Abfrage von `GITHUB_PAT`/Mail/Admin-Account — das bleibt wie im Bare-Metal-Flow dem Web-Setup-Assistenten (`/setup`) vorbehalten.

---

## 1. Gemeinsame Grundlagen

Beide Scripts leben am Repo-Root, Stil (Farben, `info`/`warn`/`die`/`section`/`ask`-Helper, Bannerformat) wird 1:1 aus `install.sh`/`update.sh` übernommen.

- **Default-Repo:** `GITHUB_REPO="toke7919/standdienst"` fest im Script hinterlegt (kein Git-Remote verfügbar, da die Scripts unabhängig von einem Checkout laufen). Überschreibbar über `GITHUB_REPO` in der generierten `.env`.
- **Default-Installationspfad:** `/opt/standdienst-docker` — bewusst abweichend vom Bare-Metal-Default `/opt/standdienst`, um Kollisionen zu vermeiden, falls beide Modi je einmal auf demselben Host ausprobiert werden. Über Argument/Prompt änderbar.
- **Release-Bezug:** gleiche GitHub-API-Abfrage- und DNS-Fallback-Logik wie in `update.sh` (`_resolve_github_api_ip`, `_github_get`, `_latest_release`) wird in beide neuen Scripts übernommen (Code-Duplikation akzeptiert, da beide Scripts eigenständig lauffähig sein sollen — kein Sourcing einer gemeinsamen Lib, um die bestehende Struktur nicht zu verändern).
- **Versionsermittlung:** `standdienst-api/version.py` im Installationsverzeichnis wird wie im Bare-Metal-Script per Python geparst.

---

## 2. `install-docker.sh`

Verwendung: `sudo bash install-docker.sh [Installationspfad]`

### Schritt 1 — Voraussetzungen
- Root-Check (`require_root`).
- Banner „Standdienst – Docker-Installation".

### Schritt 2 — Docker installieren
- Prüfen: `command -v docker` und `docker compose version`.
- Falls eines fehlt: offizielles Convenience-Script ausführen (`curl -fsSL https://get.docker.com | sh`), danach `systemctl enable --quiet docker && systemctl start docker`.
- Falls beides vorhanden: Version anzeigen, Schritt überspringen.

### Schritt 3 — Konfiguration abfragen
1. Installationspfad (Argument oder Prompt, Default `/opt/standdienst-docker`).
2. Web-Port: Prompt mit Default `80`, gleiche Validierung wie in `install.sh` (numerisch, Range 1–65535, Belegungsprüfung via `ss`/`netstat`).
3. Öffentliche URL (`FRONTEND_URL`): Prompt, Vorschlag `http://<erkannte-Server-IP>` (via `hostname -I`) als Default, freie Eingabe möglich (z. B. `https://verein.example.org`).
4. Zusammenfassung anzeigen, `[J/n]`-Bestätigung wie im Bare-Metal-Script.

### Schritt 4 — Release laden
- Neuestes Release über GitHub-API ermitteln, Tarball herunterladen, in temporäres Verzeichnis entpacken.
- Enthaltene Verzeichnisse `standdienst-api/`, `standdienst-frontend/` sowie `docker-compose.yml` nach `$INSTALL_DIR` kopieren.
- Falls `$INSTALL_DIR` bereits existiert (Re-Installation): vorhandene `.env` und `docker-compose.override.yml` werden dabei nicht berührt (siehe Schritt 5/6 — Erzeugung ist idempotent, überschreibt nur bei Fehlen).

### Schritt 5 — `.env` generieren
Nur wenn `$INSTALL_DIR/.env` noch nicht existiert (Re-Installation überschreibt keine bestehenden Secrets):

```
SECRET_KEY=<openssl rand -base64 48, gekürzt auf 64 Zeichen>
POSTGRES_PASSWORD=<openssl rand, 32 Zeichen>
FRONTEND_URL=<abgefragter Wert>
FRONTEND_PORT=<abgefragter Web-Port>
SESSION_COOKIE_SECURE=<true wenn FRONTEND_URL mit https:// beginnt, sonst false>
GITHUB_REPO=toke7919/standdienst
COMPOSE_FILE=docker-compose.yml:docker-compose.override.yml
```

`chmod 600`, kein spezieller Owner nötig (Root betreibt Docker-Compose direkt, kein separater Service-User wie beim Bare-Metal-Modell).

### Schritt 6 — Override-Datei anlegen
Nur falls `$INSTALL_DIR/docker-compose.override.yml` noch nicht existiert: leere Datei mit Kommentar-Vorlage anlegen, z. B.:

```yaml
# Lokale Anpassungen. Diese Datei wird von update-docker.sh NIE überschrieben.
# Beispiel:
# services:
#   frontend:
#     ports:
#       - "8080:80"
```

### Schritt 7 — Bauen & Starten
```bash
cd "$INSTALL_DIR"
docker compose build
docker compose up -d
```
Datenbankmigrationen laufen automatisch beim Start des `api`-Containers (bestehender `command:`-Eintrag `flask db upgrade && gunicorn ...` in `docker-compose.yml`).

### Schritt 8 — Health-Check & Abschluss
- Kurze Wartezeit, dann `docker compose ps` prüfen, ob `api`- und `frontend`-Container laufen; bei Fehlschlag `die` mit Hinweis auf `docker compose logs`.
- Abschluss-Banner mit: Installationspfad, erreichbarer URL (`FRONTEND_URL`), Hinweis auf `/setup` als nächsten Schritt, Pfad zur Override-Datei für spätere Anpassungen.

---

## 3. `update-docker.sh`

Verwendung: `sudo bash update-docker.sh [--check] [--yes] [Installationspfad]` — gleiche Flag-Semantik wie `update.sh`.

### Schritt 1 — Vorbereitung
- Root-Check, Argumente parsen (`--check`, `--yes`/`-y`, Installationspfad-Default `/opt/standdienst-docker`).
- Prüfen: `$INSTALL_DIR/docker-compose.yml`, `$INSTALL_DIR/.env`, `$INSTALL_DIR/standdienst-api/version.py` vorhanden — sonst `die`.
- `.env` laden (`GITHUB_REPO`).

### Schritt 2 — Versionsvergleich
- Identisch zu `update.sh`: aktuelle Version aus `standdienst-api/version.py`, neueste Version über GitHub-API, Release-Notes anzeigen, `--check`/Bestätigung wie im Original.

### Schritt 3 — Backup
```bash
cd "$INSTALL_DIR"
docker compose exec -T api python3 - <<PYEOF
from wsgi import app
with app.app_context():
    from app.api.admin.backup import run_backup
    try:
        name = run_backup(label='vor_update_${LATEST}')
        print(name)
    except Exception as e:
        print(f'FEHLER: {e}')
        raise SystemExit(1)
PYEOF
```
Bei Fehlschlag: `warn` (kein Abbruch), analog zum Bare-Metal-Verhalten ("kein Passwort gesetzt?").

### Schritt 4 — Release laden & entpacken
Identisch zu Schritt 4 in `install-docker.sh` (Tarball-Download + Extraktion in temporäres Verzeichnis).

### Schritt 5 — Dateien synchronisieren
```bash
rsync -a --delete \
    --exclude='.env' \
    --exclude='docker-compose.override.yml' \
    "$EXTRACTED/standdienst-api/" "$INSTALL_DIR/standdienst-api/"
rsync -a --delete \
    "$EXTRACTED/standdienst-frontend/" "$INSTALL_DIR/standdienst-frontend/"
cp "$EXTRACTED/docker-compose.yml" "$INSTALL_DIR/docker-compose.yml"
```
`.env` und `docker-compose.override.yml` werden nie angefasst.

### Schritt 6 — Neu bauen & starten
```bash
cd "$INSTALL_DIR"
docker compose build
docker compose up -d
```
Migrationen laufen wieder automatisch beim `api`-Start.

### Schritt 7 — Health-Check & Abschluss
- Warten (`sleep 2`), dann prüfen ob `api`-Container läuft (`docker compose ps` bzw. `docker compose exec api true` als Erreichbarkeitstest); bei Fehlschlag `die` mit Hinweis auf `docker compose logs api -n 50`.
- Abschluss-Banner mit Versionssprung (alt → neu), analog `update.sh`.

---

## 4. Korrektur an `docker-compose.yml`

Aktuell hat nur der `scheduler`-Service `restart: unless-stopped`. `db`, `redis`, `api`, `frontend` haben keine Restart-Policy und würden einen Host-Reboot nicht überleben (Container ohne Restart-Policy starten nach einem Neustart des Docker-Daemons nicht automatisch neu). Ergänzung von `restart: unless-stopped` bei `db`, `redis`, `api`, `frontend`, damit eine „vollautomatische" Installation auch einen Server-Neustart übersteht. Der `frontend-dev`-Profildienst (nur für lokale Entwicklung) bleibt unverändert ohne Restart-Policy.

---

## 5. Fehlerbehandlung

Folgt durchgehend dem bestehenden Muster (`set -euo pipefail`, `die()` bricht mit Exit 1 und roter Meldung ab, keine verschluckten Fehler):

- Docker-Installation schlägt fehl → `die` mit Hinweis, `get.docker.com`-Ausgabe wird nicht unterdrückt.
- Port belegt → erneute Abfrage (wie im Bare-Metal-Script), kein Abbruch.
- GitHub-API nicht erreichbar → gleiche DNS-Fallback- und Fehlermeldungslogik wie `update.sh`.
- `docker compose build`/`up` schlägt fehl → Script bricht ab (`set -e`), keine automatische Rollback-Logik (Backup aus Schritt 3 dient als manueller Wiederherstellungspunkt, wie beim Bare-Metal-Update).
- Backup schlägt fehl → `warn`, Update läuft weiter (bestehendes Verhalten aus `update.sh` übernommen).

---

## 6. Testing/Verifikation

Da beide Scripts Root-Rechte und einen echten Docker-Daemon benötigen, keine Unit-Tests im `pytest`-Sinne. Verifikation erfolgt manuell/exploratorisch:

- `bash -n install-docker.sh` / `bash -n update-docker.sh` — Syntaxcheck (wie bisher für alle Root-Scripts üblich).
- Manueller Testlauf auf einer frischen Debian/Ubuntu-VM oder einem Docker-in-Docker-Testcontainer: Installation → `/setup` erreichbar → Update-Lauf → Version steigt, Override-Datei und `.env` bleiben unverändert (per `md5sum`-Vergleich vor/nach Update prüfbar).
