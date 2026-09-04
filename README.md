# Standdienst

Webanwendung zur Verwaltung von Freiwilligendiensten und Essensspenden bei Veranstaltungen. Mehrere Organisationen (Instanzen) teilen sich eine Installation, jede mit eigenem Slug, Branding, Datenschutzerklärung und getrenntem Datenbestand.

---

## Funktionsumfang

- Schichtplanung: Stände, Termine und Schichten anlegen, Helfer melden sich selbst an und ab
- Essensspenden: Spendenarten je Termin, Helfer tragen ihren Beitrag ein
- Rollen: Global-Admin, Instanz-Admin, Organisator, Helfer
- Export als PDF, ODS und iCal (Dienstplan, Essensspenden)
- Verschlüsselte Backups (AES-256-GCM), Download und Wiederherstellung über die Weboberfläche
- E-Mail: Anmeldebestätigung, Erinnerung 24 Stunden vorher, Einladungs- und Reset-Links
- Zwei-Faktor-Anmeldung (TOTP mit Backup-Codes) und Passkeys für Admins und Organisatoren
- DSGVO: Datenexport, Auskunft per Mail, Soft-Delete mit Pseudonymisierung
- CAPTCHA über ALTCHA, ohne externen Dienst

---

## Installation

Vorausgesetzt wird Debian 12 oder Ubuntu 22.04+ mit root-Zugriff. Docker samt Compose-Plugin installiert das Skript bei Bedarf aus dem offiziellen Docker-Repository.

### Mit Skript

```bash
git clone https://github.com/toke7919/standdienst.git
cd standdienst
sudo bash install-docker.sh
```

Das Skript fragt nach Web-Port und öffentlicher URL, legt eine `.env` mit zufälligem `SECRET_KEY` und `POSTGRES_PASSWORD` an und startet die Container. Installiert wird im aktuellen Verzeichnis, nichts wird nach `/opt` kopiert.

Eigene Änderungen an der Compose-Konfiguration gehören in die dabei angelegte `docker-compose.override.yml`. Updates lassen diese Datei unberührt.

### Von Hand

```bash
git clone https://github.com/toke7919/standdienst.git
cd standdienst
cp .env.example .env
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env
docker compose up --build -d
```

Docker und das Compose-Plugin (v2) müssen dafür bereits installiert sein.

### Erstkonfiguration

Nach dem Start `http://<öffentliche URL>/setup` im Browser aufrufen und den Assistenten durchlaufen: ersten Admin anlegen, Basis-URL setzen, optional SMTP hinterlegen.

Hinter einem Reverse Proxy mit HTTPS gehört in die `.env`:

```
FRONTEND_URL=https://deine-domain.de
SESSION_COOKIE_SECURE=true
```

---

## Update

Im Installationsverzeichnis ausführen:

```bash
cd /pfad/zur/installation
sudo bash update-docker.sh          # mit Rückfrage
sudo bash update-docker.sh --yes    # ohne Rückfrage
sudo bash update-docker.sh --check  # nur prüfen, nichts ändern
```

Das Skript lädt das neueste Release, erstellt vorab ein Backup (sofern ein Backup-Passwort gesetzt ist), baut die Images neu und startet die Container. `.env` und `docker-compose.override.yml` bleiben unverändert.

Bei einer Installation von Hand:

```bash
git pull
docker compose up --build -d
```

---

## Deinstallation

```bash
cd /pfad/zur/installation
docker compose down -v      # -v löscht auch die Datenbank
cd .. && rm -rf standdienst
```

---

## Backup und Wiederherstellung

Backups werden im Admin-Bereich unter **Einstellungen → Backup** erstellt, heruntergeladen und wiederhergestellt. Die Dateien (`.sdbackup`) sind mit AES-256-GCM verschlüsselt; das Passwort wird dort einmalig gesetzt.

---

## Konfiguration (`.env`)

| Variable | Pflicht | Bedeutung |
|----------|---------|-----------|
| `SECRET_KEY` | ja | Schlüssel für Sessions und JWT, mindestens 32 Zeichen |
| `POSTGRES_PASSWORD` | nein | Datenbankpasswort (Standard `standdienst`). PostgreSQL übernimmt den Wert nur bei der ersten Einrichtung des Datenverzeichnisses. Wird er später geändert, muss das Passwort auch in der laufenden Datenbank angepasst werden (`ALTER USER standdienst PASSWORD …`). |
| `FRONTEND_URL` | nein | Öffentliche URL, wird für E-Mail-Links verwendet (Standard `http://localhost`) |
| `FRONTEND_PORT` | nein | Host-Port des Frontend-Containers (Standard `80`) |
| `SESSION_COOKIE_SECURE` | nein | `true`, sobald die Anwendung über HTTPS läuft (Standard `false`) |
| `COMPOSE_FILE` | nein | Setzt `install-docker.sh` auf `docker-compose.yml:docker-compose.override.yml` |

---

## Lokale Entwicklung

```bash
# Backend
cd standdienst-api
export SECRET_KEY="dev-key-32bytes-minimum-!!!!!!" DATABASE_URL="sqlite:///dev.db"
.venv/bin/flask --app wsgi db upgrade
.venv/bin/flask --app wsgi run --debug

# Frontend (zweites Terminal)
cd standdienst-frontend
npm install
npm run dev   # Vite-Dev-Server auf Port 5173, Proxy auf das Backend
```

Tests:

```bash
cd standdienst-api && .venv/bin/pytest
cd standdienst-frontend && npm run test
```

---

## Aufbau

```
standdienst-api/        Flask-REST-API (Gunicorn)
standdienst-frontend/   Vue-3-SPA, Vite-Build nach standdienst-api/static/dist/
docker-compose.yml      Container: db, redis, api, scheduler, frontend
install-docker.sh       Installation
update-docker.sh        Update auf das neueste Release
```

Die SPA wird als statische Dateien ausgeliefert. Im Container-Setup übernimmt nginx das Routing auf Port 80.

---

## Lizenz

[GNU Affero General Public License v3.0](LICENSE). Wer eine geänderte Fassung über ein Netzwerk anbietet, muss den Quellcode der Änderungen zugänglich machen.
