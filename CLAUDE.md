# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Was dieses Projekt ist

**Standdienst** ist eine deutschsprachige REST-API + Vue-3-SPA zur Verwaltung von Freiwilligendiensten (Schichten) und Essensspenden bei Veranstaltungen.

**Multi-Instanz-Betrieb:** Eine Plattform hostet beliebig viele organisatorische Einheiten (Vereine, Events) als isolierte Instanzen mit eigenem Slug, Branding, Datenschutzerklärung und Daten.

**Vier Rollen:**
- **Global-Admin** – voller Plattformzugriff, instanzübergreifend
- **Instanz-Admin** – Organizer mit `is_instance_admin=True`; voller Zugriff auf eigene Instanz inkl. Einstellungen
- **Organisator** – operativer Zugriff (Schichten, Termine, Anmeldungen); kein Zugriff auf Instanz-Einstellungen
- **Volunteer** – Self-Service (eigene Instanz): Schichten buchen, Essen spenden, Profil verwalten

---

## Designprinzipien – PFLICHTREGELN

1. **Erst fragen, dann umsetzen.** Bei jeder Unklarheit zuerst nachfragen.
2. **Keine hypothetischen Features.** Keine Abstraktion, keine Vorbereitung auf Szenarien, die nicht explizit angefordert wurden.
3. **Kein Gold-Plating.** Nur das Nötigste, um die Anforderung zu erfüllen.
4. **Fehler nie verschlucken.** Jeder Fehler wird geloggt und der aufrufenden Schicht gemeldet.
5. **Additive-only Migrations.** Alembic-Migrationen dürfen Spalten/Tabellen nur hinzufügen, niemals entfernen oder umbenennen.
6. **Optimistic Locking bei PUT-Endpunkten.** Jeder PUT-Request muss `updated_at` senden. Backend prüft gegen DB-Wert; Abweichung → 409 Conflict.

---

## Arbeitsweise

**Bei Unklarheit fragen, nicht annehmen.** Wenn für eine gute Umsetzung Informationen fehlen, nachfragen — und zwar als Auswahl konkreter Optionen mit Empfehlung, nicht als offene Frage. Mehrere offene Punkte in einer Frage bündeln.

Diese Datei fortlaufend pflegen: Wenn in einer Session eine Projektentscheidung fällt, eine Konvention entsteht oder eine Korrektur zu einem wiederkehrenden Muster kommt, gehört das hier hinein — knapp, an der passenden Stelle. Chronologische Etappen-Erzählung gehört nicht hierher – die steht in der Commit-Historie; diese Datei ist ein Nachschlagewerk aus Konventionen und Entscheidungen, kein Tagebuch.

---

## Tests

**Backend:** pytest, ein Lauf über `standdienst-api/tests/`. Läuft gegen SQLite in-memory (siehe `tests/conftest.py`) – kein separater Datenbank-Container nötig, dadurch schnell und CI-tauglich.

**Frontend:** Vitest mit jsdom und `@testing-library/vue`, ein Lauf über `standdienst-frontend/src/`.

**Jede neue Funktion und jeder neue Screen bringt Tests mit** — das ist verbindlich, nicht optional. Konkret heißt das:

| Neu dazu | Was getestet wird |
|---|---|
| Vue-Komponente | Die Regeln, die beim Umbau am ehesten kaputtgehen — Props-Varianten, Zustände (leer/gefüllt/Grenzfälle), Events. Vorbild: `Pagination.test.js` prüft die Seitenzahl-Kürzung (Ellipsis) je nach aktueller Seite. |
| View/Screen | Was bei welcher Datenlage erscheint und was nicht: Leerzustand, Lade- und Fehlerzustand. |
| API-Route (`standdienst-api/app/api/`) | Statuscode, Antwortform und **immer die Autorisierung** — greift der Instanz-/Rollen-Filter (`require_staff`/`require_instance_admin`/`require_admin`/`require_volunteer`), kommt ein Fremdzugriff (falsche Instanz, falsche Rolle) wirklich nicht durch. Vorbild: `test_admin_guards.py`, `test_security.py`, `test_roles.py`. |
| Geteilte Backend-Logik (`app/utils/`) | Unit-Test in `standdienst-api/tests/`. |
| Fehlerbehebung | Zuerst der Test, der den Fehler reproduziert, dann die Behebung. |

**Für reine Shell-Scripts** (`install.sh`, `update.sh`, `uninstall.sh`, `install-docker.sh`, `update-docker.sh` – kein pytest/Vitest-Test möglich) gilt stattdessen realer Ausführungsnachweis als Abnahme: `bash -n` für die Syntax, plus mindestens ein echter Lauf gegen laufende Infrastruktur (z. B. ein echter Docker-Daemon), dokumentiert mit Befehl und tatsächlichem Ergebnis – nicht nur behauptet.

---

## Commands

```bash
# Backend – Entwicklungsserver
cd standdienst-api
export SECRET_KEY="dev-key-32bytes-minimum-!!!!!!" DATABASE_URL="sqlite:///dev.db"
.venv/bin/flask --app wsgi run --debug

# Tests
.venv/bin/pytest                                                          # alle
.venv/bin/pytest tests/test_roles.py -v                                   # eine Datei
.venv/bin/pytest tests/test_registration.py::test_welcome_setup_sets_password_and_logs_in -v  # einzelner Test
.venv/bin/pytest --cov=app --cov-report=term-missing                      # mit Coverage

# Datenbankmigrationen
.venv/bin/flask --app wsgi db migrate -m "beschreibung"
.venv/bin/flask --app wsgi db upgrade

# requirements.txt neu kompilieren (nach requirements.in-Änderung)
.venv/bin/pip-compile requirements.in -o requirements.txt

# Frontend
cd standdienst-frontend
npm run dev    # Vite Dev-Server mit Proxy auf Backend
npm run build  # Build → standdienst-api/static/dist/
npm run test   # Vitest, einmaliger Lauf
npm run test:watch  # Vitest im Watch-Modus
```

---

## Architektur-Überblick

### Backend (`standdienst-api/`)

Flask-App mit App-Factory-Pattern (`app/__init__.py`). Blueprints:
- `setup_bp` – Ersteinrichtung, nur erreichbar solange `GlobalSettings.setup_complete = False`
- `auth_bp` – Login (Admin/Org/Volunteer), 2FA, JWT-Refresh, Passwort-Reset
- `public_bp` – Öffentliche Endpunkte: Instanz-Info, ALTCHA-Captcha, Registrierung, Welcome-Token
- `volunteer_bp` – Schichten, Essensspenden, Profil, DSGVO-Export
- `admin_bp` – CRUD für alle Instanz-Daten, Settings, Export/Import, Backup, Update-Check

Das Frontend wird als SPA aus `standdienst-api/static/dist/` serviert (Vite-Build-Output).

### Auth-Decorators (`app/utils/auth.py`)

```python
@require_admin          # Nur Global-Admins
@require_staff          # Admin oder Organizer; setzt g.instance, g.current_user, g.role
@require_instance_admin # require_staff + is_instance_admin=True
@require_volunteer      # Volunteer der richtigen Instanz, nicht soft-gelöscht
```

### JWT-System

- Access Token: 15 min, HttpOnly-Cookie `access_token`
- Refresh Token: 30 Tage, HttpOnly-Cookie `refresh_token`
- Identity-Format: `"admin_1"`, `"organizer_2"`, `"volunteer_3"`
- `jwt_version`-Claim: wird bei Passwort-Änderung inkrementiert → Sofort-Invalidierung aller Sessions

### Frontend (`standdienst-frontend/src/`)

- **`api/`** – Axios-Wrapper pro Bereich (`client.js` mit JWT + CSRF-Interceptor + 401-Refresh)
- **`stores/`** – Pinia: `auth.js` (User-State), `instance.js` (Instanz-Kontext), `ui.js` (Toasts/Confirm), `setup.js` (Setup-Status-Cache)
- **`layouts/`** – `AdminLayout.vue` (Sidebar + Instanz-Selector), `VolunteerLayout.vue`
- **`composables/useSort.js`** – wiederverwendbare Tabellen-Sortierung

### ALTCHA-CAPTCHA

Proof-of-Work-CAPTCHA ohne externe Abhängigkeiten (`app/utils/captcha.py`). Der Client löst SHA-256-Hashes clientseitig; das Backend verifiziert via HMAC. Challenge gültig 10 Minuten. Registrierung sendet `altcha: "<base64-payload>"`.

### E-Mail-System (`app/utils/mail.py`)

`is_mail_configured()` prüft zuerst Env-Vars, dann `MailSettings`-Tabelle. Alle Mail-Builder geben vollständige HTML-Strings zurück. `send_mail()` hat 3 Versuche mit exponentiellem Backoff.

Transaktions-Mails (kein Opt-out): Passwort-Reset, Welcome-Token, Schicht-Bestätigung.  
`notifications_enabled` (opt-in) steuert Erinnerungsmail 1 Tag vorher.  
`email_confirmation_enabled` (opt-out, default=True) steuert Bestätigungsmail nach Schicht-Anmeldung.

### Mobile-Layout-Muster

Admin-Views mit Tabellen verwenden `md:hidden` gestapelte Liste + `hidden md:table` Desktop-Tabelle (nicht bei Registrations-View).

---

## Datenmodell

### Globale Models

| Model | Besonderheiten |
|-------|----------------|
| `Instance` | `slug` eindeutig, `is_active` |
| `Admin` | `is_primary`, TOTP 2FA + Backup-Codes, Passkey-Support |
| `Organizer` | `is_instance_admin`, Many-to-Many Instanzen via `organizer_instances` |
| `GlobalSettings` | `setup_complete`, `github_pat`, `timezone` (IANA), SMB-Backup-Config |
| `MailSettings` | SMTP (DB-gespeichert, überschreibt Env-Vars) |
| `ActivityLog` | `instance_id=NULL` = globaler Eintrag |

### Instanzgebundene Models

| Model | Besonderheiten |
|-------|----------------|
| `Volunteer` | E-Mail optional, Soft-Delete, `consent_given_at`, `notifications_enabled` (opt-in), `email_confirmation_enabled` (opt-out, default=True) |
| `Stand` | `sort_order` |
| `EventDate` | `(instance_id, date)` UNIQUE, `formatted` (deutsches Datumsformat) |
| `Shift` | `(stand_id, event_date_id, start_time, end_time)` UNIQUE, `is_full`, `spots_left`, `time_range` |
| `Registration` | `(volunteer_id, shift_id)` UNIQUE, `registered_by_admin`, `guest_name` (für Admin-Einträge ohne Volunteer-Konto) |
| `FoodDonationType` | Pro Instanz + EventDate, `delivery_datetime`, `delivery_location` |
| `FoodDonation` | `needs_refrigeration`, `guest_name`, FK zu Volunteer (optional) + FoodDonationType |
| `SiteSettings` | 1:1 zu Instanz; `registration_deadline`, `unregister_deadline_hours` (Stunden vor Schichtbeginn), `shifts_enabled`, `food_donations_enabled`, `site_locked` |

### Volunteer-Eigenschaften

```python
volunteer.soft_delete()      # name=[gelöscht-{id}], email=None, password_hash='!'
volunteer.is_deleted         # @property (deleted_at is not None)
volunteer.has_login          # email gesetzt + gültiger password_hash
volunteer.display_name       # first_name + last_name, Fallback auf name
volunteer.generate_welcome_token(604800)  # SHA-256, 7 Tage TTL
```

---

## API-Endpunkte

### setup_bp (`/api/setup`)

Nur erreichbar solange `setup_complete = False` (außer `/status`).

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/status` | `{setup_complete, has_admin, maintenance_mode}` |
| POST | `/admin` | Ersten Admin anlegen |
| POST | `/config` | Basis-URL, GitHub-PAT, Copyright, Zeitzone |
| POST | `/mail` | SMTP-Konfiguration |
| POST | `/finish` | `setup_complete=True` setzen |

### auth_bp (`/api/auth`)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/login` | Admin/Organizer-Login |
| POST | `/volunteer-login` | Volunteer-Login |
| POST | `/2fa/verify` | 2FA-Code prüfen |
| POST | `/2fa/setup` / `/2fa/confirm` / `/2fa/disable` | TOTP verwalten |
| POST | `/refresh` | Access-Token erneuern |
| POST | `/logout` | Cookies clearen |
| POST | `/forgot-password` / `/reset-password` | Admin/Org Passwort-Reset |
| GET | `/me` | Aktueller Nutzer (inkl. `notifications_enabled`, `email_confirmation_enabled`) |

### public_bp (`/api/public`)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/<slug>/info` | Instanz-Info + Branding + `mail_enabled`, `unregister_deadline_hours` |
| GET | `/<slug>/captcha` | ALTCHA-Challenge generieren |
| POST | `/<slug>/register` | Registrierung (`altcha` Pflichtfeld, E-Mail optional) |
| GET/POST | `/<slug>/welcome/<token>` | Welcome-Token prüfen / Passwort einrichten |
| GET | `/<slug>/datenschutz` | Datenschutzerklärung-HTML |
| POST | `/<slug>/forgot-password` / `/<slug>/reset-password` | Volunteer Passwort-Reset |

### volunteer_bp (`/api/volunteer`)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/<slug>/shifts` | Schichten (mit `is_registered`) |
| POST | `/<slug>/shifts/<id>/register` | Anmelden (Row-Level Lock + Bestätigungsmail) |
| DELETE | `/<slug>/shifts/<id>/register` | Abmelden (prüft `unregister_deadline_hours`) |
| GET | `/<slug>/my-registrations` | Meine Anmeldungen |
| GET | `/<slug>/my-registrations/ical` | Als iCal exportieren |
| GET/POST/DELETE | `/<slug>/food-donations` | Essensspenden |
| GET | `/<slug>/meine-daten` | DSGVO Art. 20 – JSON-Export |
| POST | `/<slug>/meine-daten/export` | DSGVO Art. 15 – Datenauskunft per E-Mail (3/Tag) |
| PUT | `/<slug>/profile` | Profil + Benachrichtigungs-Toggles |
| DELETE | `/<slug>/profile` | Soft-Delete (DSGVO) |

### admin_bp (`/api/admin`) – Auswahl

| Methode | Pfad | Decorator | Beschreibung |
|---------|------|-----------|--------------|
| GET/POST | `/<slug>/volunteers` | require_staff | Volunteer-Liste / anlegen |
| GET | `/<slug>/volunteers/<id>/detail` | require_staff | Helfer-Detail inkl. Schichten + Spenden |
| DELETE | `/<slug>/volunteers/<id>` | require_instance_admin | Soft-Delete |
| DELETE | `/<slug>/volunteers/<id>/permanent` | require_admin | Permanentes Löschen |
| GET/PUT | `/<slug>/settings` | require_instance_admin | Instanz-Einstellungen |
| GET/PUT | `/settings/global` | require_admin | Globale Einstellungen |
| GET/PUT | `/settings/mail` | require_admin | Mail-Einstellungen |
| GET | `/<slug>/export/<format>` | require_staff | CSV/Excel/ODS/iCal-Export |
| POST | `/<slug>/import/shifts/<format>` | require_staff | Daten-Import (Admin + Organisator) |
| POST | `/backup/create` | require_admin | DB-Backup (AES-GCM + SMB) |
| GET | `/update/check` | require_admin | Update-Verfügbarkeit (GitHub Releases API) |
| GET | `/<slug>/dsgvo/processing-record` | require_instance_admin | Art. 30 Verarbeitungsverzeichnis |

---

## Registrierungsflow

### Mit E-Mail
```
POST /<slug>/register {first_name, last_name, email, altcha, consent?}
  → 201 + E-Mail mit Welcome-Link (7 Tage gültig)

POST /<slug>/welcome/<raw_token> {password}
  → 200 {user} + JWT-Cookies
```

### Ohne E-Mail (Anonym)
```
POST /<slug>/register {first_name, last_name, altcha, consent?}
  → 201 {user: {role: 'volunteer', email: null}} + JWT-Cookies
```

`consent` wird nur erzwungen wenn `SiteSettings.privacy_policy_html` gesetzt ist.

---

## Race-Condition-Schutz bei Schicht-Anmeldung

```python
shift = Shift.query.with_for_update().get(shift_id)  # SELECT ... FOR UPDATE
if shift.spots_left <= 0:
    return error('Schicht ist voll', 409)
if _has_time_overlap(volunteer_id, shift):
    return error('Zeitüberschneidung', 409)
db.session.add(Registration(...))
db.session.commit()
_send_shift_confirmation(...)  # fire-and-forget nach commit
```

---

## APScheduler-Jobs (`app/utils/scheduler.py`)

```python
purge_tokens()       # stündlich – abgelaufene Reset-/Welcome-Tokens löschen
purge_logs()         # täglich 03:00 – ActivityLogs nach log_retention_months
smb_backup()         # täglich 02:30 – nur wenn GlobalSettings.smb_enabled = True
purge_volunteers()   # monatlich 1. 04:00 – nur wenn volunteer_retention_months gesetzt
_send_reminders()    # täglich 08:00 – für Volunteers mit notifications_enabled=True
```

Scheduler startet nur wenn `not app.config['TESTING']`.

---

## Frontend-Routing

```
/setup                             → SetupWizard (redirect → / wenn setup_complete=True)
/admin/login[/2fa]                 → Admin/Org-Login + 2FA
/admin/:slug/volunteers            → Helfer-Liste
/admin/:slug/volunteers/:id        → Helfer-Detailseite (Schichten + Spenden)
/admin/:slug/settings              → Instanz-Einstellungen (nur isInstanceAdmin)
/:slug/login                       → Volunteer-Login
/:slug/register                    → Registrierung
/:slug/welcome/:token              → Passwort einrichten
/:slug/shifts                      → Schichten
/:slug/my-shifts                   → Meine Anmeldungen
/:slug/food                        → Essensspenden
/:slug/profile                     → Profil + Benachrichtigungs-Toggles + DSGVO
```

Router-Guard: `beforeEach` prüft `setup_complete` via gecachtem `useSetupStore().check()`.

---

## Passwort-Richtlinien

| Rolle | Mindestanforderungen |
|-------|----------------------|
| **Volunteer** | 8 Zeichen |
| **Admin / Organizer** | 12 Zeichen, mind. je 1 Groß-/Kleinbuchstabe, Ziffer, Sonderzeichen |

Implementiert in `validate_password_strength(password, role='volunteer')`.

---

## Environment-Variablen

### Pflicht

| Variable | Zweck |
|----------|-------|
| `SECRET_KEY` | Flask-Session + JWT (min. 32 Zeichen) |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/dbname` |

### Optional

| Variable | Default | Zweck |
|----------|---------|-------|
| `JWT_SECRET_KEY` | `SECRET_KEY` | Separater JWT-Schlüssel |
| `FRONTEND_URL` | `http://localhost:5173` | CORS + E-Mail-Links |
| `RATELIMIT_STORAGE_URI` | `memory://` | Redis: `redis://127.0.0.1:6379/0` |
| `SESSION_COOKIE_SECURE` | `false` | Produktion: `true` |
| `FAIL2BAN_LOG` | `logs/auth.log` | Fail2Ban-kompatibles Login-Log |
| `MAIL_SERVER` | `''` | SMTP-Host (alternativ per DB-MailSettings) |
| `GUNICORN_BIND` | `0.0.0.0:8420` | Bind-Adresse |
| `SETUP_ALLOWED_IPS` | `''` | IPs für `/api/setup/*`; leer = alle; localhost immer erlaubt |
| `ALTCHA_MAX_NUMBER` | `100000` | Schwierigkeit des PoW-CAPTCHAs |

---

## Git-Konventionen

### Branch-Namensschema

`feat/`, `fix/`, `refactor/`, `chore/`, `docs/`

### Workflow

1. Branch anlegen – niemals direkt auf `main`
2. Conventional Commits auf Deutsch: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`
3. Tests ausführen – kein Commit ohne bestandene Tests
4. PR erstellen und mergen
5. **Release Pflicht** nach `feat/` und `fix/`: `version.py` aktualisieren + Git-Tag + GitHub-Release – direkt im Anschluss an den Merge, nicht erst auf Nachfrage warten

```bash
# standdienst-api/version.py
VERSION = "X.Y.Z"
VERSION_DATE = "YYYY-MM-DD"

git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z --title "vX.Y.Z – Kurzbeschreibung" --notes "..."
```

**Kein CHANGELOG.md** – Release-Notes ausschließlich in GitHub Releases.

### Semantic Versioning

| PR-Typ | Versionserhöhung |
|--------|-----------------|
| `feat/` | Minor (Y) |
| `fix/` | Patch (Z) |
| Breaking Change | Major (X) |

---

## Deployment (Produktion)

- **Gunicorn**: gthread Worker, `CPU*2+1` Workers, 2 Threads, Port 8420
- **Nginx**: Reverse Proxy auf 8420; `/static/` + `/uploads/` direkt serviert
- **systemd**: `standdienst.service` (After: postgresql + redis-server)
- **install.sh**: Port abfragen → Pakete → Venv → `.env` generieren → Migrations → Build → systemd/Nginx → verweist auf `/setup`

---

## Bekannte Einschränkungen

| Bereich | Problem | Schwere |
|---------|---------|---------|
| CSP | `style-src 'unsafe-inline'` nötig für Vue `:style`-Bindings und `colorPalette.js` (`element.style.setProperty`). `script-src 'self'` (kein `unsafe-inline`) ist gesetzt. | Niedrig |
