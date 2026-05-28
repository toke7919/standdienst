# Standdienst v2

Webbasierte Plattform zur Verwaltung von Freiwilligendiensten und Essensspenden bei Veranstaltungen. Mehrere Organisationen (Instanzen) laufen auf einer gemeinsamen Installation mit eigenem Branding, Datenschutzerklärung und Daten.

---

## Features

- **Schichtverwaltung** – Stände, Termine, Schichten anlegen; Helfer melden sich selbst an/ab
- **Essensspenden** – Spendenarten pro Termin, Helfer tragen sich mit Beschreibung ein
- **Multi-Instanz** – beliebig viele Organisationen auf einer Installation, je mit eigenem Slug + Logo
- **Rollen** – Global-Admin, Instanz-Admin, Organisator, Volunteer (Self-Service)
- **Export** – ODS/PDF Dienstplan als Stundenplan-Tabelle, Essensspenden-Listen, iCal
- **Backup/Restore** – AES-256-GCM-verschlüsselte Backups, Download und Wiederherstellung über Web-UI
- **E-Mail** – Anmeldebestätigung, Erinnerung (24 h vorher), Welcome-Link, Passwort-Reset
- **2FA** – TOTP + Backup-Codes für Admins und Organisatoren
- **Passkeys** – WebAuthn-Anmeldung für Admins und Organisatoren
- **DSGVO** – Datenexport (Art. 20), Auskunft per Mail (Art. 15), Soft-Delete (Pseudonymisierung)
- **CAPTCHA** – ALTCHA Proof-of-Work (serverside, keine externen Dienste)

---

## Installation

### Option A: Docker (empfohlen)

```bash
git clone https://github.com/toke7919/standdienst_v2.git
cd standdienst_v2
cp .env.example .env
# SECRET_KEY generieren und in .env eintragen:
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env
docker compose up --build -d
```

Danach im Browser `http://localhost/setup` aufrufen und die Erstkonfiguration abschließen.

**Voraussetzungen:** Docker + Docker Compose v2

**HTTPS** (mit Reverse Proxy davor):
In `.env` setzen:
```bash
FRONTEND_URL=https://deine-domain.de
SESSION_COOKIE_SECURE=true
```

### Option B: Bare-Metal (Debian/Ubuntu)

```bash
git clone https://github.com/toke7919/standdienst_v2.git
cd standdienst_v2
sudo bash install.sh
```

Das Skript fragt nach Installationspfad und Port, richtet PostgreSQL, Redis, Gunicorn (systemd) und Nginx ein. Am Ende öffnest du `/setup` im Browser und schließt die Erstkonfiguration ab.

**Voraussetzungen:** Debian 12 / Ubuntu 22.04+, Root-Zugriff

**HTTPS** (nach der Installation):
```bash
certbot --nginx -d <domain>
```

---

## Update

```bash
sudo bash update.sh          # interaktiv
sudo bash update.sh --yes    # ohne Rückfragen
sudo bash update.sh --check  # nur prüfen, nicht anwenden
```

Das Update-Skript erstellt automatisch ein Backup vor dem Update.

Bei Docker:
```bash
git pull
docker compose up --build -d
```

---

## Backup & Restore

Backups werden im Admin-Bereich unter **Einstellungen → Backup** erstellt, heruntergeladen und wiederhergestellt. Das Format ist AES-256-GCM-verschlüsselt (`.sdbackup`).

---

## Konfiguration

### Docker (`.env`)

| Variable | Pflicht | Beschreibung |
|----------|---------|--------------|
| `SECRET_KEY` | ✓ | Flask-Session + JWT (min. 32 Zeichen) |
| `POSTGRES_PASSWORD` | – | Datenbankpasswort (Standard: `standdienst`) |
| `FRONTEND_URL` | – | Öffentliche URL für E-Mail-Links (Standard: `http://localhost`) |
| `FRONTEND_PORT` | – | Port des Frontend-Containers (Standard: `80`) |
| `SESSION_COOKIE_SECURE` | – | `true` bei HTTPS (Standard: `false`) |

### Bare-Metal (`standdienst-api/.env`)

| Variable | Pflicht | Beschreibung |
|----------|---------|--------------|
| `SECRET_KEY` | ✓ | Flask-Session + JWT (min. 32 Zeichen) |
| `DATABASE_URL` | ✓ | `postgresql://user:pass@host:5432/dbname` |
| `FRONTEND_URL` | – | Basis-URL für E-Mail-Links |
| `RATELIMIT_STORAGE_URI` | – | Redis: `redis://127.0.0.1:6379/0` |
| `FAIL2BAN_LOG` | – | Pfad für Login-Fail-Log (Standard: `logs/auth.log`) |
| `SETUP_ALLOWED_IPS` | – | Kommagetrennte IPs für `/setup`; leer = alle erlaubt |
| `ALTCHA_MAX_NUMBER` | – | CAPTCHA-Schwierigkeit (Standard: `100000`) |
| `MAIL_SERVER` | – | SMTP-Host (alternativ über Web-UI konfigurierbar) |

---

## Lokale Entwicklung

```bash
# Backend
cd standdienst-api
export SECRET_KEY="dev-key-32bytes-minimum-!!!!!!" DATABASE_URL="sqlite:///dev.db"
.venv/bin/flask --app wsgi db upgrade
.venv/bin/flask --app wsgi run --debug

# Frontend (in separatem Terminal)
cd standdienst-frontend
npm install
npm run dev   # Vite-Dev-Server mit Proxy auf Backend (Port 5173)
```

Tests:
```bash
cd standdienst-api
.venv/bin/pytest                          # alle Tests
.venv/bin/pytest tests/test_roles.py -v   # einzelne Datei
```

---

## Architektur

```
standdienst-api/        Flask REST-API (Gunicorn, Port 8420)
standdienst-frontend/   Vue 3 SPA (Vite-Build → api/static/dist/)
docker-compose.yml      Docker-Setup (db, redis, api, scheduler, frontend)
install.sh              Bare-Metal-Installationsskript
update.sh               Update auf neues GitHub-Release
uninstall.sh            Vollständige Deinstallation
```

Die SPA wird als statische Dateien aus `standdienst-api/static/dist/` serviert. Im Docker-Setup übernimmt nginx (Port 80) das Routing; bei Bare-Metal leitet Nginx Port 80/443 an Gunicorn weiter.

---

## Lizenz

Privates Projekt – alle Rechte vorbehalten.
