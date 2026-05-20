# Sicherheitsaudit – Standdienst v2

**Datum:** 2026-05-20  
**Version:** 3.22.0  
**Methode:** Manuelles Code-Review aller sicherheitsrelevanten Dateien

---

## Gesamtbewertung

Die Grundarchitektur ist solide: JWT mit Versionskontrolle, bcrypt-Passwort-Hashing, CSRF Double-Submit-Cookie, Row-Level-Locking, Rate-Limiting. Es gibt jedoch **3 kritische**, **5 hohe** und **6 mittlere** Schwachstellen, die adressiert werden sollten.

| Schweregrad | Anzahl |
|-------------|--------|
| KRITISCH    | 3      |
| HOCH        | 5      |
| MITTEL      | 6      |
| NIEDRIG     | 4      |

---

## KRITISCH

### K-1 · `exec()` in update.py — Potenzielle Code-Ausführung

**Datei:** `standdienst-api/app/api/admin/update.py:27`  
**OWASP:** A03:2021 – Injection

```python
with open(os.path.join(_api_root(), 'version.py')) as f:
    exec(f.read(), ns)  # noqa: S102
```

`version.py` wird via `exec()` ausgeführt, um die Versionsnummer zu lesen. Gelingt es einem Angreifer, diese Datei zu manipulieren (z.B. durch einen kompromittierten Update-Prozess oder schwache Dateisystemberechtigungen), kann beliebiger Python-Code mit den Rechten des Gunicorn-Prozesses ausgeführt werden.

**Fix:**
```python
import re

def _installed_version() -> str:
    path = os.path.join(_api_root(), 'version.py')
    with open(path) as f:
        m = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', f.read(), re.M)
    return m.group(1) if m else 'unknown'
```

---

### K-2 · SQL-Injection via Backup-Restore

**Datei:** `standdienst-api/app/api/admin/backup.py:94–111`  
**OWASP:** A03:2021 – Injection

```python
for stmt in stmts:
    conn.execute(text(stmt))  # Raw SQL aus der Backup-Datei
```

`_restore_from_bytes()` führt jede nicht-kommentierte Zeile eines Backup-SQL-Strings direkt aus. Ein manipuliertes Backup (z.B. von einer externen Quelle) kann beliebige SQL-Befehle ausführen — Daten exfiltrieren, Accounts anlegen, die DB löschen.

**Erschwerend:** Endpunkt K-3 erlaubt das Hochladen eines externen Backups inklusive eigenem Schlüssel.

**Fix:** Backup-Integrität via HMAC-SHA-256-Signatur sicherstellen. Signatur wird beim Erstellen mit geschrieben, beim Restore geprüft, bevor SQL ausgeführt wird.

```python
import hmac, hashlib

def _sign(data: bytes, key: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()

def _verify_and_restore(data: bytes, key: bytes) -> None:
    sig, payload = data[:32], data[32:]
    expected = _sign(payload, key)
    if not hmac.compare_digest(sig, expected):
        raise ValueError('Backup-Signatur ungültig')
    _restore_from_bytes(payload)
```

---

### K-3 · AES-Schlüssel über API abrufbar + Restore akzeptiert externen Schlüssel

**Datei:** `standdienst-api/app/api/admin/backup.py:214–218` und `:165–181`  
**OWASP:** A02:2021 – Cryptographic Failures

```python
@admin_bp.route('/backup/export-key', methods=['GET'])
def export_backup_key():
    key = _derive_aes_key()
    return ok({'key': base64.b64encode(key).decode()})
```

Der vollständige AES-256-GCM-Schlüssel kann von jedem Global-Admin per GET-Request abgerufen werden. Kombiniert mit dem Upload-Endpunkt (beliebiges `.enc`-File hochladen) und der Möglichkeit, beim Restore einen externen Schlüssel mitzugeben, ergibt sich eine vollständige Angriffskette:

1. Admin A stiehlt den Schlüssel via `export-key`
2. Erstellt ein präpariertes Backup mit bösartigem SQL
3. Verschlüsselt es mit dem gestohlenen Schlüssel
4. Lädt es hoch, ruft Restore auf → beliebiger SQL-Code läuft

**Fix:**
- `export-backup-key` entfernen oder hinter eine Passwort-Bestätigung stellen
- Restore keine externen Schlüssel akzeptieren (nur mit dem installations-eigenen Schlüssel)
- Passwort-Challenge (Admin-Passwort) vor Restore

---

## HOCH

### H-1 · XSS via HTML-Sanitizer: Attributwerte nicht escaped

**Datei:** `standdienst-api/app/utils/sanitizer.py:35`  
**OWASP:** A03:2021 – XSS

```python
attr_str = ''.join(f' {k}="{v}"' for k, v in safe_attrs.items())
```

Enthält ein Attributwert `"` (z.B. in einem `class`-Wert), bricht er aus dem Anführungszeichen-Kontext aus. Der Browser parst dann ein zusätzliches Attribut. Beispiel:

```
Eingabe:  class="foo" onload="alert(1)"  (als EINZELNER Attributwert übergeben)
Ausgabe:  class="foo" onload="alert(1)"  ← Browser-XSS
```

Zwar werden `on*`-Attribute aus dem `attrs`-Dict gefiltert (Zeile 49), aber der Attributwert-Break ermöglicht, beliebige Attribute in den generierten HTML-String einzuschleusen, ohne durch den Filter zu gehen.

**Außerdem:** Das `style`-Attribut ist via `'*': {'class', 'id', 'style'}` global erlaubt, aber CSS-Werte werden nicht validiert. Moderne Browser verhindern `expression()` und `url(javascript:)`, aber CSS-Injection für Phishing/Tracking bleibt möglich.

**Fix:**
```python
import html as html_mod

attr_str = ''.join(
    f' {k}="{html_mod.escape(v, quote=True)}"'
    for k, v in safe_attrs.items()
)
```

Und `style` aus `*`-Whitelist entfernen oder CSS-Werte gegen eine Whitelist prüfen.

---

### H-2 · Fehlende HTTP-Security-Header

**Datei:** `standdienst-api/app/__init__.py` (kein `after_request`-Hook für Header)  
**OWASP:** A05:2021 – Security Misconfiguration

Kein einziger Sicherheits-Header wird gesetzt:

| Header | Status |
|--------|--------|
| `Content-Security-Policy` | ❌ fehlt |
| `X-Content-Type-Options: nosniff` | ❌ fehlt |
| `X-Frame-Options: DENY` | ❌ fehlt |
| `Referrer-Policy` | ❌ fehlt |
| `Strict-Transport-Security` | ❌ fehlt |
| `Permissions-Policy` | ❌ fehlt |

**Fix** — neuer Hook in `app/__init__.py`:

```python
@app.after_request
def _security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
    if not app.debug:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

CSP ist wegen `'unsafe-inline'` (Tailwind) auf der SPA-Seite schwierig, aber für die API-Antworten gilt: `default-src 'none'` reicht für reine JSON-Antworten.

---

### H-3 · Datei-Upload: nur Endung geprüft, kein Magic-Bytes-Check

**Datei:** `standdienst-api/app/api/admin/settings.py:64–83`  
**OWASP:** A04:2021 – Insecure Design

```python
ext = (file.filename or '').rsplit('.', 1)[-1].lower()
if ext not in _ALLOWED_LOGO:
    return error(...)
file.save(os.path.join(upload_dir, filename))
```

Nur die Dateiendung wird geprüft. Ein Angreifer kann eine SVG-Datei mit eingebettetem JavaScript hochladen — SVGs haben keine eindeutigen Magic Bytes und sind valides XML mit `<script>`-Support. Da Logos direkt über `/uploads/` serviert werden, kann diese SVG im Browser als aktives HTML/JS ausgeführt werden.

**Fix:**
- SVG aus `_ALLOWED_LOGO` entfernen oder SVG-Inhalt auf erlaubte Elemente sanieren
- Für PNG/JPEG/GIF/WebP: Pillow zur Bildvalidierung nutzen

```python
from PIL import Image
import io

try:
    img = Image.open(io.BytesIO(file.read()))
    img.verify()  # prüft Integrität
    file.seek(0)
except Exception:
    return error('Ungültige Bilddatei', 400)
```

---

### H-4 · Secrets (SMTP-Passwort, SMB-Passwort, GitHub PAT) im Klartext in der DB

**Datei:** `standdienst-api/app/models/instance.py:43,45,68`  
**OWASP:** A02:2021 – Cryptographic Failures

```python
smb_password = db.Column(db.String(500), nullable=True)
github_pat    = db.Column(db.String(500), nullable=True)
mail_password = db.Column(db.String(500), nullable=False, default='')
```

Drei Credentials werden unverschlüsselt in der PostgreSQL-Datenbank gespeichert. Bei einem DB-Dump (Backup-Leak, SQL-Injection, unsichere psql-Zugriffsrechte) sind alle drei sofort lesbar.

**Fix:** Symmetrische Verschlüsselung mit dem `SECRET_KEY` der Installation:

```python
from cryptography.fernet import Fernet
import hashlib, base64

def _fernet():
    key = base64.urlsafe_b64encode(hashlib.sha256(current_app.config['SECRET_KEY'].encode()).digest())
    return Fernet(key)

# Speichern: Fernet(_fernet()).encrypt(value.encode()).decode()
# Lesen:     Fernet(_fernet()).decrypt(value.encode()).decode()
```

Oder: Credentials gar nicht in der DB speichern, sondern ausschließlich via Umgebungsvariablen konfigurieren (12-Factor).

---

### H-5 · `target="_blank"` ohne erzwungenes `rel="noopener noreferrer"`

**Datei:** `standdienst-api/app/utils/sanitizer.py:15`  
**OWASP:** A03:2021 – XSS (Reverse Tabnabbing)

```python
'a': {'href', 'title', 'target', 'rel'},
```

`target` ist erlaubt, aber der Sanitizer erzwingt kein `rel="noopener noreferrer"` wenn `target="_blank"` gesetzt ist. Das ermöglicht Reverse-Tabnabbing: Die geöffnete Seite kann über `window.opener` die ursprüngliche Seite auf eine Phishing-URL umleiten.

**Fix:** In `_filter_attrs()` automatisch ergänzen:

```python
if result.get('target') == '_blank':
    result['rel'] = 'noopener noreferrer'
```

---

## MITTEL

### M-1 · CAPTCHA: nur 40 mögliche Antworten, vorhersehbares PRNG

**Datei:** `standdienst-api/app/utils/captcha.py`  
**OWASP:** A07:2021 – Authentication Failures

```python
a = random.randint(1, 20)   # nicht-kryptografisches random
b = random.randint(1, 20)
```

- `random.randint` ist kein kryptografisches PRNG (vorhersehbar nach einigen Ausgaben)
- Nur 39 mögliche Antwortwerte (2–40). Mit Rate-Limit von 10/min: brute-force in ≤4 Minuten
- Kein IP-Limit auf CAPTCHA-Generierung selbst

**Fix:** Antwortbereich vergrößern und CAPTCHA-Generierung Rate-Limiten:

```python
import secrets
a = secrets.randbelow(90) + 10   # 10–99
b = secrets.randbelow(90) + 10   # 10–99
# → 180 mögliche Antworten + Rate-Limit auf /captcha
```

Mittelfristig: hCaptcha oder Altcha (privacy-first, self-hosted möglich) integrieren.

---

### M-2 · Mindestpasswort-Länge für Volunteers: 6 Zeichen

**Datei:** `standdienst-api/app/utils/auth.py`  
**OWASP:** A07:2021 – Authentication Failures

```python
if len(password) < 6:   # Volunteers
    return False
```

OWASP empfiehlt mindestens 8 Zeichen; NIST SP 800-63B sogar 8 als Minimum. 6 Zeichen ermöglichen triviale Brute-Force-Angriffe (besonders für Accounts ohne 2FA).

**Fix:** Auf 8 Zeichen erhöhen. Frontend-Checkliste anpassen.

---

### M-3 · Gunicorn bindet auf `0.0.0.0`

**Datei:** `standdienst-api/gunicorn.conf.py:7`  
**OWASP:** A05:2021 – Security Misconfiguration

```python
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:8420')
```

Default-Binding auf alle Interfaces. Wenn Nginx nicht konfiguriert ist oder ausfällt, ist Gunicorn direkt (ohne TLS, ohne WAF) erreichbar. Gunicorn ist kein hardened Webserver.

**Fix:** Default auf `127.0.0.1:8420` ändern.

---

### M-4 · Exception-Details an Client gesendet (Backup, Import)

**Dateien:**  
- `standdienst-api/app/api/admin/backup.py:184`  
- `standdienst-api/app/api/admin/import_.py` (breites `except Exception`)  
**OWASP:** A09:2021 – Security Logging Failures

```python
return error(f'Restore fehlgeschlagen: {e}', 500)   # e enthält Stack-Info
```

Interne Ausnahme-Nachrichten (Dateinamen, DB-Struktur, Stack-Traces) werden an den Client gesendet. Das hilft Angreifern beim Reconnaissance.

**Fix:** Generische Fehlermeldung an Client, Details nur ins Log:

```python
current_app.logger.exception('Restore fehlgeschlagen')
return error('Backup-Wiederherstellung fehlgeschlagen', 500)
```

---

### M-5 · `SESSION_COOKIE_SECURE` standardmäßig `False`

**Datei:** `standdienst-api/app/config.py`  
**OWASP:** A02:2021 – Cryptographic Failures

```python
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
```

Die Flask-Session (für 2FA-`pending_2fa`) wird standardmäßig auch über HTTP gesendet. Auf einer Produktions-Installation hinter HTTPS ist dies unkritisch, aber es fehlt ein expliziter Hinweis im `install.sh`, dass diese Variable auf `true` gesetzt werden muss.

**Fix:** `SESSION_COOKIE_SECURE=true` in der generierten `.env` durch `install.sh` explizit setzen.

---

### M-6 · Rate-Limiting: `X-Forwarded-For` ist spoofbar; Fallback auf `127.0.0.1`

**Datei:** `standdienst-api/app/extensions.py`  
**OWASP:** A07:2021 – Authentication Failures

```python
return (
    request.environ.get('HTTP_X_REAL_IP')
    or request.environ.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
    or request.remote_addr
    or '127.0.0.1'   # ← alle scharen sich unter einem Limit!
)
```

Ist kein `X-Real-IP` gesetzt (z.B. direkte Verbindung), wird `X-Forwarded-For` verwendet — der vom Client beliebig gesetzt werden kann. Der Fallback auf `127.0.0.1` lässt alle Anfragen ohne erkannte IP unter demselben Rate-Limit laufen.

**Fix:** Nginx muss `proxy_set_header X-Real-IP $remote_addr;` konfigurieren. In der App: Fallback auf `request.remote_addr` (nie auf einen Fixed-String):

```python
return (request.environ.get('HTTP_X_REAL_IP')
        or request.remote_addr
        or 'unknown')
```

---

## NIEDRIG

### N-1 · JWT-Tokens bei Logout nicht invalidiert

**Datei:** `standdienst-api/app/api/auth.py` (logout-Endpoint)  
**OWASP:** A01:2021 – Broken Access Control

Logout löscht nur die Cookies. Ein bereits extrahierter Access-Token (15 Minuten Gültigkeit) bleibt vollständig gültig. Das ist ein inhärenter JWT-Tradeoff, aber in einem Sicherheitskontext erwähnenswert.

**Teilfix:** Bei Logout `jwt_version` inkrementieren (wird bei Passwort-Änderung bereits getan). Dadurch werden alle Tokens sofort invalidiert (Refresh schlägt fehl).

---

### N-2 · Test-Mail-Endpoint ohne Empfänger-Validierung

**Datei:** `standdienst-api/app/api/admin/settings.py`  
**OWASP:** A07:2021 – Authentication Failures

```python
to = data.get('email') or getattr(g.current_user, 'email', None)
```

Ein Global-Admin kann Test-Mails an beliebige Adressen senden. Missbrauchspotenzial als Spam-Relay begrenzt (erfordert Admin-Rechte), aber grundsätzlich unerwünscht.

**Fix:** Nur an `g.current_user.email` senden, konfigurierbar machen.

---

### N-3 · `data:` URI in `img[src]` nicht explizit erlaubt, aber auch nicht verboten

**Datei:** `standdienst-api/app/utils/sanitizer.py:51`

Die URL-Regex erlaubt nur `http://`, `https://`, `mailto:`. `data:`-URIs für Inline-Bilder sind damit blockiert — das ist korrekt für `img[src]`, da `data:text/html,...` als XSS missbrauchbar wäre.

Kein akuter Fix nötig, aber explizite `data:image/*`-Erlaubnis (falls inline-Bilder benötigt) sollte mit Vorsicht eingeführt werden.

---

### N-4 · Keine API-Versionierung

Alle Endpunkte laufen unter `/api/...` ohne Versionsnummer. Bei zukünftigen Breaking Changes (z.B. für mobile Apps oder Drittintegration) kein rückwärtskompatibles Routing möglich.

**Empfehlung:** `/api/v1/...` einführen, wenn externe Clients hinzukommen.

---

## Was explizit gut gemacht ist

- **JWT `jwt_version`-Claim**: Sofortige Invalidierung aller Sessions bei Passwort-Änderung — vorbildlich
- **Row-Level-Locking** bei Schicht-Anmeldungen: kein Overbooking möglich
- **bcrypt** für Passwort-Hashing mit ausreichendem Work-Factor
- **CSRF Double-Submit-Cookie** mit `SameSite=Strict`
- **`secrets.token_urlsafe(32)`** für alle Token-Generierungen (kryptografisch sicher)
- **Soft-Delete** mit Pseudonymisierung (DSGVO-konform)
- **Rate-Limiting** auf alle sensitiven Endpoints (Redis-backed)
- **CORS**: Einzelner erlaubter Origin, kein Wildcard
- **`require_staff` prüft Instanz-Zugehörigkeit**: Kein Cross-Instance-Zugriff möglich
- **`updated_at`-Optimistic-Locking** (in CLAUDE.md verankert)
- **Additive-only Migrations**: keine destruktiven Schemaänderungen

---

## Priorisierte Behebungsreihenfolge

| Priorität | ID | Maßnahme | Aufwand |
|-----------|-----|----------|---------|
| 1 | K-1 | `exec()` ersetzen durch Regex-Parser | 15 min |
| 2 | H-1 | Attributwerte in Sanitizer escapen | 15 min |
| 3 | H-2 | Security-Header Hook in `__init__.py` | 20 min |
| 4 | H-5 | `rel="noopener noreferrer"` erzwingen | 10 min |
| 5 | M-4 | Exception-Details nicht an Client senden | 30 min |
| 6 | M-2 | Volunteer-Passwort-Minimum auf 8 Zeichen | 10 min |
| 7 | M-3 | Gunicorn Default auf `127.0.0.1` | 5 min |
| 8 | K-2 | Backup-HMAC-Signatur | 2 h |
| 9 | K-3 | Key-Export entfernen, Passwort-Challenge für Restore | 1 h |
| 10 | H-3 | Pillow-Bildvalidierung für Upload | 1 h |
| 11 | H-4 | Credentials in DB verschlüsseln | 3 h |
| 12 | M-1 | CAPTCHA-Antwortbereich vergrößern | 30 min |
