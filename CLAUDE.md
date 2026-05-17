# CLAUDE.md – Standdienst v2

Dieses File gibt Claude Code Kontext über das Projekt, die Architektur und die Konventionen.

## Was dieses Projekt ist

**Standdienst v2** ist eine mehrsprachig ausgelegte, deutschsprachige REST-API + Vue-3-SPA zur Verwaltung von Freiwilligendiensten (Schichten) und Essensspenden bei Veranstaltungen.

**Multi-Instanz-Betrieb:** Eine Plattform hostet beliebig viele organisatorische Einheiten (Vereine, Events) als isolierte Instanzen mit eigenem Slug, Branding, Datenschutzerklärung und Daten.

**Drei Rollen:**
- **Global-Admin** – voller Plattformzugriff, instanzübergreifend
- **Instanz-Admin** – Organizer mit `is_instance_admin=True`; voller Zugriff auf eigene Instanz inkl. Einstellungen
- **Organisator** – operativer Zugriff (Schichten, Termine, Anmeldungen); kein Zugriff auf Instanz-Einstellungen
- **Volunteer** – Self-Service (eigene Instanz): Schichten buchen, Essen spenden, Profil verwalten

**Aktueller Stand:** v3.0.0-beta.1 (2026-05-17) – Erster Beta-Meilenstein mit Drei-Rollen-System, DSGVO und passwortlosem Registrierungsflow.

---

## Projektstruktur

```
standdienst_v2/
├── standdienst-api/              # Flask REST-API (Python)
│   ├── app/
│   │   ├── __init__.py           # App-Factory, Blueprint-Registrierung, Error-Handler
│   │   ├── config.py             # Env-basierte Konfiguration (Config + TestingConfig)
│   │   ├── extensions.py         # Flask-Extensions (db, jwt, mail, limiter, cors, migrate)
│   │   ├── api/
│   │   │   ├── auth.py           # Login, 2FA, Refresh, Passwort-Reset (Admin/Org/Volunteer)
│   │   │   ├── public.py         # Öffentliche Routes (Info, Registrierung, Welcome, DSGVO)
│   │   │   ├── volunteer.py      # Volunteer-Bereich (Schichten, Essen, Profil, DSGVO-Export)
│   │   │   └── admin/
│   │   │       ├── __init__.py   # admin_bp Blueprint
│   │   │       ├── instances.py  # Instanz-CRUD
│   │   │       ├── organizers.py # Organizer-CRUD + Instanz-Zuordnung
│   │   │       ├── admins.py     # Admin-CRUD
│   │   │       ├── volunteers.py # Volunteer-CRUD, Soft-Delete, permanentes Löschen
│   │   │       ├── stands.py     # Schicht-Orte (CRUD + Sortierung)
│   │   │       ├── dates.py      # Event-Termine (CRUD)
│   │   │       ├── shifts.py     # Schichten (CRUD)
│   │   │       ├── registrations.py  # Admin-seitige Anmeldungen
│   │   │       ├── food.py       # Essen-Kategorien + Spenden-Übersicht
│   │   │       ├── settings.py   # SiteSettings, GlobalSettings, MailSettings
│   │   │       ├── activity.py   # ActivityLog-Abfrage
│   │   │       ├── dashboard.py  # Admin-Dashboard-Stats
│   │   │       ├── export.py     # CSV/Excel/ODS/iCal-Export
│   │   │       ├── import_.py    # CSV/XLSX/ODS-Import
│   │   │       ├── backup.py     # DB-Dump + AES-GCM-Verschlüsselung + SMB-Upload
│   │   │       └── update.py     # Software-Update-Check
│   │   ├── models/
│   │   │   ├── instance.py       # Instance, GlobalSettings, MailSettings, organizer_instances
│   │   │   ├── admin.py          # Admin (2FA, Reset-Token)
│   │   │   ├── organizer.py      # Organizer (is_instance_admin, Many-to-Many Instanzen)
│   │   │   ├── volunteer.py      # Volunteer (Soft-Delete, Welcome-Token, Email optional)
│   │   │   ├── shifts.py         # Stand, EventDate, Shift, Registration
│   │   │   ├── food.py           # FoodDonationType, FoodDonation
│   │   │   ├── settings.py       # SiteSettings (pro Instanz)
│   │   │   ├── activity.py       # ActivityLog (Audit-Trail)
│   │   │   └── __init__.py
│   │   ├── schemas/              # Marshmallow-Validierungs-Schemas (ein File pro Model)
│   │   └── utils/
│   │       ├── auth.py           # Auth-Decorators, Password-Validation
│   │       ├── scheduler.py      # APScheduler-Jobs (Token-Purge, Log-Cleanup, Backup)
│   │       ├── mail.py           # E-Mail-Templates (Reset, Welcome, Registrierung)
│   │       ├── captcha.py        # Mathe-CAPTCHA (Session-basiert, 5 min TTL)
│   │       ├── sanitizer.py      # HTML-Whitelist-Sanitizer
│   │       ├── color.py          # Farb-Utilities
│   │       └── responses.py      # Response-Helper (ok, created, error, paginated)
│   ├── migrations/               # Alembic-Migrationen (Flask-Migrate)
│   │   └── versions/
│   │       └── c1efeb76ffc8_initial_schema_volunteer_welcome_token.py
│   ├── tests/
│   │   ├── conftest.py           # Fixtures (TestingConfig, SQLite in-memory, client)
│   │   ├── test_auth.py
│   │   ├── test_public.py
│   │   ├── test_registration.py  # Passwortloser Registrierungsflow + Welcome-Token
│   │   ├── test_roles.py         # Drei-Rollen-Zugriffskontrolle + Soft/Permanent-Delete
│   │   └── test_dsgvo.py         # DSGVO: Datenauskunft, Soft-Delete, Datenschutzerklärung
│   ├── wsgi.py                   # Gunicorn Entry: create_app()
│   ├── gunicorn.conf.py          # Gunicorn-Produktionskonfiguration
│   ├── requirements.in           # Abhängigkeiten (Quelle)
│   ├── requirements.txt          # Kompiliert (pip-compile, Python 3.13)
│   └── .gitignore
├── standdienst-frontend/         # Vue 3 + Vite + Tailwind SPA
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── api/
│   │   │   ├── client.js         # Axios-Instanz (JWT + CSRF-Interceptor, 401-Refresh)
│   │   │   ├── auth.js
│   │   │   ├── public.js         # register, welcomeInfo, welcomeSetup, getPrivacyPolicy
│   │   │   ├── volunteer.js      # Schichten, Essen, Profil, getMeineDaten
│   │   │   └── admin.js          # Vollständige Admin-API inkl. permanentDeleteVolunteer
│   │   ├── stores/
│   │   │   ├── auth.js           # User-State, Login-Actions, isStaff/isVolunteer
│   │   │   ├── instance.js       # Instanz-Kontext
│   │   │   └── ui.js             # Toast, Modal, Confirm-Dialog
│   │   ├── router/index.js       # Vue Router 4 (lazy-loading, Route-Guards)
│   │   ├── layouts/
│   │   │   ├── AdminLayout.vue   # Sidebar + Instanz-Selector
│   │   │   └── VolunteerLayout.vue
│   │   ├── views/
│   │   │   ├── public/           # Landing, Impressum, PrivacyPolicy
│   │   │   ├── admin/            # 20 Views (Dashboard, CRUD, Export, Backup, …)
│   │   │   └── volunteer/        # Login, Register, WelcomeSetup, Shifts, Profile, …
│   │   └── components/           # ToastContainer, Modal, ConfirmDialog, Pagination, LoadingSpinner
│   ├── package.json
│   ├── vite.config.js            # Build → standdienst-api/static/dist/
│   ├── tailwind.config.js
│   └── postcss.config.js
├── install.sh                    # Vollständiges Debian/Ubuntu-Installations-Script
├── .gitignore
└── README.md
```

---

## Technology-Stack

| Bereich | Technologie | Version |
|---------|-------------|---------|
| Web-Framework | Flask | 3.1.3 |
| ORM | Flask-SQLAlchemy + SQLAlchemy | 3.1.1 |
| Migrationen | Flask-Migrate (Alembic) | 4.1.0 |
| Authentifizierung | Flask-JWT-Extended | 4.7.4 |
| Passwort-Hashing | bcrypt | 5.0.0 |
| 2FA | PyOTP (TOTP) | 2.9.x |
| E-Mail | Flask-Mail | 0.10.0 |
| Rate-Limiting | Flask-Limiter[redis] | 4.1.1 |
| CORS | Flask-CORS | 6.0.2 |
| Validierung | Marshmallow + marshmallow-sqlalchemy | 3.21 / 1.1 |
| Verschlüsselung | cryptography (AES-GCM) | 48.0.0 |
| Scheduling | APScheduler | 3.11.2 |
| PDF-Export | WeasyPrint | 62.x |
| Excel-Export | openpyxl | 3.1.x |
| ODS-Export | odfpy | 1.4.x |
| iCal-Export | icalendar | 5.0.x |
| QR-Codes | qrcode[pil] + Pillow | 8.0 / 10.x |
| Datenbank | PostgreSQL 14+ | psycopg2-binary |
| Cache / Rate-Limit | Redis | 5.2.1 |
| WSGI-Server | Gunicorn (gthread) | 23.0.0 |
| Frontend | Vue 3 + Vite + Pinia + Vue Router | 3.4 / 5.4 / 2.1 / 4.3 |
| CSS | Tailwind CSS | 3.4.0 |
| HTTP-Client | Axios | 1.7.0 |
| Node.js | ≥ 20 | |

---

## Commands

```bash
# Entwicklungsserver (Backend)
cd standdienst-api
export SECRET_KEY="dev-key-32bytes-minimum-!!!!!!" DATABASE_URL="sqlite:///dev.db"
.venv/bin/flask --app wsgi run --debug

# Alle Tests
.venv/bin/pytest

# Einzelne Datei / einzelner Test
.venv/bin/pytest tests/test_roles.py -v
.venv/bin/pytest tests/test_registration.py::test_welcome_setup_sets_password_and_logs_in -v

# Mit Coverage
.venv/bin/pytest --cov=app --cov-report=term-missing

# Datenbankmigrationen
.venv/bin/flask --app wsgi db migrate -m "beschreibung"
.venv/bin/flask --app wsgi db upgrade

# requirements.txt neu kompilieren (nach requirements.in-Änderung)
.venv/bin/pip-compile requirements.in -o requirements.txt

# Frontend
cd standdienst-frontend
npm install
npm run dev    # Vite Dev-Server (Proxy auf Backend)
npm run build  # Build → standdienst-api/static/dist/

# Vollinstallation (Debian/Ubuntu als root)
sudo bash install.sh [--dir /opt/standdienst]
```

---

## Authentifizierung & Sicherheit

### JWT-System

- **Access Token**: 15 Minuten, HttpOnly-Cookie (`access_token`)
- **Refresh Token**: 30 Tage, HttpOnly-Cookie (`refresh_token`)
- **Location**: `['headers', 'cookies']` – beides unterstützt
- **CSRF**: Double-Submit-Cookie, SameSite=Strict
- **Identity-Format**: `"admin_1"`, `"organizer_2"`, `"volunteer_3"`

### Auth-Decorators (app/utils/auth.py)

```python
@require_admin          # Nur Global-Admins (role='admin' im JWT)
@require_staff          # Admin oder Organizer; prüft Instanz-Zugriff via <slug>
@require_instance_admin # Admin oder Organizer mit is_instance_admin=True
@require_volunteer      # Volunteer der richtigen Instanz, nicht soft-gelöscht
```

**`require_staff`** setzt `g.instance`, `g.current_user`, `g.role`. Organizer ohne Zugriff auf Instanz → 403.

**`require_instance_admin`** wie `require_staff`, aber Organizer braucht zusätzlich `is_instance_admin=True`.

### Passwort-Validierung

Mindestens 8 Zeichen, 1 Ziffer, 1 Sonderzeichen (`validate_password_strength()`).

### Rate-Limits

| Endpoint | Limit |
|----------|-------|
| Admin/Org Login | 5/min |
| Volunteer Login | 5/min |
| 2FA-Verify | 10/min |
| Registrierung | 10/min |
| Passwort vergessen | 5/min |
| Passwort zurücksetzen | 10/min |
| Schicht-Toggle | 30/min |
| Global Default | 200/h |

Redis-Backend (`RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0`) für worker-übergreifendes Rate-Limiting.

### CAPTCHA

Mathe-Addition in Flask-Session gespeichert, 5-Minuten-TTL, einmalig konsumiert.

---

## Datenmodell

### Globale Models

| Model | Zweck | Besonderheiten |
|-------|-------|----------------|
| `Instance` | Organisationseinheit | `slug` eindeutig, URL-Identifier, `is_active` |
| `Admin` | Global-Admin | `is_primary`, TOTP 2FA, Reset-Token (1h) |
| `Organizer` | Instanz-Verantwortlicher | `is_instance_admin`, Many-to-Many Instanzen |
| `GlobalSettings` | Plattform-Einstellungen | Base-URL, SMB-Backup-Config, Log-Retention |
| `MailSettings` | SMTP-Konfiguration | (DB-gespeichert, optional via .env) |
| `ActivityLog` | Audit-Trail | `instance_id=NULL` = globaler Eintrag |

**`organizer_instances`** (Many-to-Many):
```
(organizer_id FK CASCADE, instance_id FK CASCADE, is_primary BOOL)
```

### Instanzgebundene Models

| Model | Besonderheiten |
|-------|----------------|
| `Volunteer` | E-Mail optional, Soft-Delete, Welcome-Token, `consent_given_at` |
| `Stand` | Schicht-Ort, `sort_order` |
| `EventDate` | `(instance_id, date)` UNIQUE, German-formatted `formatted` |
| `Shift` | `(stand_id, event_date_id, start_time, end_time)` UNIQUE, `is_full`, `spots_left` |
| `Registration` | `(volunteer_id, shift_id)` UNIQUE, `registered_by_admin` |
| `FoodDonationType` | Pro Instanz + EventDate, `delivery_datetime` |
| `FoodDonation` | `needs_refrigeration`, FK zu Volunteer + FoodDonationType |
| `SiteSettings` | 1:1 zu Instanz; Branding, Locks, Deadlines, `privacy_policy_html` |

### Volunteer-Besonderheiten

```python
volunteer.soft_delete()      # name=[gelöscht-{id}], email=None, password_hash='!'
volunteer.is_deleted         # @property (deleted_at is not None)
volunteer.has_login          # email gesetzt + gültiger password_hash
volunteer.generate_welcome_token(86400)  # SHA-256, 24h TTL, gibt raw zurück
volunteer.is_welcome_token_valid        # prüft hash + expiry
```

### ActivityLog-Typen

```
SHIFT_REGISTER, SHIFT_UNREGISTER
FOOD_REGISTER, FOOD_UNREGISTER
LOGIN_SUCCESS, LOGIN_FAIL
VOLUNTEER_REGISTER
AUDIT_SETTINGS, AUDIT_DATA, AUDIT_ORGANIZER, AUDIT_ADMIN
```

---

## API-Endpunkte

### auth_bp (`/api/auth`)

| Methode | Pfad | Decorator | Beschreibung |
|---------|------|-----------|--------------|
| POST | `/login` | – | Admin/Organizer-Login |
| POST | `/volunteer-login` | – | Volunteer-Login |
| POST | `/2fa/verify` | – | 2FA-Code prüfen |
| POST | `/2fa/setup` | require_staff | Secret generieren |
| POST | `/2fa/confirm` | require_staff | 2FA aktivieren |
| POST | `/2fa/disable` | require_staff | 2FA deaktivieren |
| POST | `/refresh` | jwt (refresh) | Access-Token erneuern |
| POST | `/logout` | – | Cookies clearen |
| POST | `/forgot-password` | – | Admin/Org Reset-Link |
| POST | `/reset-password` | – | Passwort zurücksetzen |
| GET | `/me` | jwt (optional) | Aktueller Nutzer |

### public_bp (`/api/public`)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/instances` | Alle aktiven Instanzen |
| GET | `/<slug>/info` | Instanz-Info + Branding (inkl. `has_privacy_policy`) |
| GET | `/<slug>/captcha` | CAPTCHA generieren |
| POST | `/<slug>/register` | Registrierung (ohne Passwort!) |
| GET | `/<slug>/welcome/<token>` | Welcome-Token prüfen → Name |
| POST | `/<slug>/welcome/<token>` | Passwort setzen + einloggen |
| GET | `/<slug>/datenschutz` | Datenschutzerklärung-HTML |
| POST | `/<slug>/forgot-password` | Volunteer Reset-Link |
| POST | `/<slug>/reset-password` | Volunteer Passwort zurücksetzen |

### volunteer_bp (`/api/volunteer`)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/<slug>/shifts` | Schichten (mit `is_registered`) |
| POST | `/<slug>/shifts/<id>/register` | Schicht anmelden |
| DELETE | `/<slug>/shifts/<id>/register` | Schicht abmelden |
| GET | `/<slug>/my-registrations` | Meine Anmeldungen |
| GET | `/<slug>/my-registrations/ical` | Als iCal exportieren |
| GET | `/<slug>/food-donations` | Essen-Spenden anzeigen |
| POST | `/<slug>/food-donations` | Essen spenden |
| DELETE | `/<slug>/food-donations/<id>` | Eigene Spende löschen |
| GET | `/<slug>/meine-daten` | DSGVO Art. 20 – JSON-Export |
| PUT | `/<slug>/profile` | Profil aktualisieren |
| DELETE | `/<slug>/profile` | Soft-Delete (DSGVO) |

### admin_bp (`/api/admin`) – Auswahl

| Methode | Pfad | Decorator | Beschreibung |
|---------|------|-----------|--------------|
| GET/POST | `/<slug>/volunteers` | require_staff / require_instance_admin | Volunteer-Liste / anlegen |
| DELETE | `/<slug>/volunteers/<id>` | require_instance_admin | Soft-Delete |
| DELETE | `/<slug>/volunteers/<id>/permanent` | require_admin | Permanentes Löschen |
| GET/PUT | `/<slug>/settings` | require_instance_admin | Instanz-Einstellungen |
| GET/PUT | `/settings/global` | require_admin | Globale Einstellungen |
| GET/PUT | `/settings/mail` | require_admin | Mail-Einstellungen |
| GET/POST | `/<slug>/stands` | require_staff / require_instance_admin | Schicht-Orte |
| GET/POST | `/<slug>/dates` | require_staff / require_instance_admin | Termine |
| GET/POST | `/<slug>/shifts` | require_staff / require_instance_admin | Schichten |
| GET/POST | `/<slug>/registrations` | require_staff / require_instance_admin | Anmeldungen |
| GET | `/<slug>/export/<format>` | require_staff | CSV/Excel/iCal-Export |
| POST | `/<slug>/import/shifts/<format>` | require_instance_admin | Daten-Import |
| POST | `/backup/create` | require_admin | DB-Backup erstellen |
| GET | `/update/check` | require_admin | Update-Verfügbarkeit |

---

## Registrierungsflow

### Mit E-Mail (Welcome-Token)
```
POST /<slug>/register {name, email, captcha_answer, consent?}
  → 201 {message: 'E-Mail mit Einrichtungslink gesendet'}
  → E-Mail mit Link: /<slug>/welcome/<raw_token> (24h gültig)

GET /<slug>/welcome/<raw_token>
  → 200 {data: {name, email}}

POST /<slug>/welcome/<raw_token> {password}
  → 200 {user: {...}}  + JWT-Cookies gesetzt
```

### Ohne E-Mail (Anonym)
```
POST /<slug>/register {name, captcha_answer, consent?}
  → 201 {user: {role: 'volunteer', email: null}}  + JWT-Cookies gesetzt
```

**Consent** wird nur erzwungen, wenn `SiteSettings.privacy_policy_html` gesetzt ist.

---

## APScheduler-Jobs

```python
# täglich 00:00 – abgelaufene Tokens löschen
purge_tokens()

# täglich 03:00 – ActivityLogs älter als log_retention_months löschen
purge_logs()

# täglich 02:30 – DB-Dump, AES-256-GCM-Verschlüsselung, SMB-Upload
smb_backup()   # nur wenn GlobalSettings.smb_enabled = True
```

Scheduler startet nur wenn `not app.config['TESTING']`.

---

## Frontend-Routing

```
/                           → Landing (öffentlich)
/impressum                  → Impressum
/admin/login                → Admin/Org-Login
/admin/login/2fa            → 2FA-Verify
/admin/...                  → Admin-Panel (requiresStaff)
/:slug/login                → Volunteer-Login
/:slug/register             → Registrierung (passwordlos)
/:slug/welcome/:token       → Passwort einrichten (Welcome-Setup)
/:slug/datenschutz          → Datenschutzerklärung
/:slug/reset-password       → Volunteer Passwort-Reset
/:slug/forgot-password      → Volunteer Passwort vergessen
/:slug/shifts               → Schichten (requiresVolunteer)
/:slug/my-shifts            → Meine Anmeldungen
/:slug/food                 → Essen-Spenden
/:slug/profile              → Profil + DSGVO-Export + Konto löschen
```

---

## Environment-Variablen

### Pflicht

| Variable | Zweck |
|----------|-------|
| `SECRET_KEY` | Flask-Session + JWT-Secret (min. 32 Zeichen!) |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/dbname` |

### Optional

| Variable | Default | Zweck |
|----------|---------|-------|
| `JWT_SECRET_KEY` | `SECRET_KEY` | Separater JWT-Schlüssel |
| `FRONTEND_URL` | `http://localhost:5173` | CORS + E-Mail-Links |
| `UPLOAD_FOLDER` | `uploads` | Datei-Upload-Verzeichnis |
| `MAX_CONTENT_LENGTH_MB` | `5` | Max. Upload-Größe in MB |
| `SESSION_COOKIE_SECURE` | `false` | Nur HTTPS-Cookies (Produktion: `true`) |
| `RATELIMIT_STORAGE_URI` | `memory://` | Redis: `redis://127.0.0.1:6379/0` |
| `FAIL2BAN_LOG` | `logs/auth.log` | Fail2Ban-kompatibles Login-Log |
| `MAIL_SERVER` | `''` | SMTP-Host |
| `MAIL_PORT` | `587` | SMTP-Port |
| `MAIL_USE_TLS` | `true` | TLS aktivieren |
| `MAIL_USERNAME` | `''` | SMTP-User |
| `MAIL_PASSWORD` | `''` | SMTP-Passwort |
| `MAIL_DEFAULT_SENDER` | `''` | Absender-Adresse |
| `GUNICORN_WORKERS` | `CPU*2+1` | Anzahl Worker-Prozesse |
| `GUNICORN_BIND` | `0.0.0.0:8420` | Bind-Adresse |

---

## Code-Qualität & Konventionen

- Sauberer, lesbarer Code; Variablen-/Funktionsnamen auf Englisch
- Funktionen max. 20 Zeilen
- DRY – keine Duplikation
- Kommentare auf Deutsch, nur wenn das **Warum** nicht offensichtlich ist
- Keine unnötigen Abstraktionen, keine hypothetische Zukunftsplanung
- Validierung nur an Systemgrenzen (User-Input, externe APIs)
- Fehler nie verschlucken; aussagekräftige Fehlermeldungen

---

## Git-Konventionen

- **Niemals direkt auf `main`** arbeiten oder pushen
- Neue Branch anlegen: `feat/xyz`, `fix/abc`, `chore/xyz`
- Conventional Commits auf Deutsch: `feat:`, `fix:`, `refactor:`, `chore:`
- Nach Merge: Branch lokal und remote löschen
- Bei jeder Änderung: `CHANGELOG.md` und ggf. Versions-Bump aktualisieren
- Beta-Versionierung: `3.0.0-beta.1`, `3.0.0-beta.2`, …

---

## Deployment (Produktion)

### Gunicorn
```python
workers = CPU * 2 + 1    # gthread Worker
threads = 2
bind = '0.0.0.0:8420'
timeout = 120
graceful_timeout = 30
max_requests = 1000 ± 100
```

### Nginx
Reverse Proxy auf Port 8420; `/static/` und `/uploads/` direkt servieren.

### systemd
```
standdienst.service → Gunicorn (After: postgresql + redis-server)
```

### install.sh
Führt vollständige Debian/Ubuntu-Installation durch:
1. Systempakete (PostgreSQL, Redis, Node.js 20, Nginx)
2. Service-User, Verzeichnisse
3. PostgreSQL + Redis konfigurieren
4. Python-Venv + Dependencies
5. Secrets generieren (`.env`)
6. Frontend bauen (`npm install && npm run build`)
7. DB-Migrationen (`flask db upgrade`)
8. systemd + Nginx einrichten

---

## Bekannte Einschränkungen

| Bereich | Problem | Schwere |
|---------|---------|---------|
| CSP | `'unsafe-inline'` im Frontend (Tailwind) | Mittel |
| Scheduler | APScheduler Worker-lokal (Multi-Worker: Jobs laufen mehrfach) | Mittel |
| Settings-Cache | Kein Cache implementiert (v2 hatte TTL-Cache, v3 noch offen) | Niedrig |
| Migrationen | Erste Migration deckt gesamtes Schema ab; kein Rollback-Szenario getestet | Mittel |
| E-Mail | Kein Retry bei SMTP-Fehler | Niedrig |
