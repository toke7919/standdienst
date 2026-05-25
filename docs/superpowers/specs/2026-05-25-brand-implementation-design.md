# Brand-Implementierung Standdienst — Design-Spec

**Datum:** 2026-05-25  
**Ansatz:** C — vollständige Überarbeitung aller Vue-Dateien  
**Scope:** ~42 Vue-Dateien + 5 Konfigurationsdateien + Asset-Kopie

---

## Ziel

Die Standdienst-Brand (Karmin/Tinte/Sand, Hanken Grotesk, Geist Mono, Ticket-Mark) wird vollständig in die bestehende Vue-3-SPA überführt. Layout-Logik und Komponentenstruktur bleiben unverändert — nur das Styling wird angepasst. Das Pro-Instanz-Theming über `applyTheme()` bleibt erhalten.

---

## 1. Token-System

### `tokens.css`
Wird nach `standdienst-frontend/src/assets/tokens.css` kopiert und als erster Import in `main.css` eingebunden:
```css
@import './tokens.css';
```
Die Originaldatei im Repo-Root bleibt als Referenz erhalten.

### Tailwind-Konfiguration (`tailwind.config.js`)
Neue benannte Farben neben dem bestehenden `primary`-System:
```js
colors: {
  ink:      'var(--color-ink)',
  muted:    'var(--color-muted)',
  sand:     'var(--color-sand)',
  'bg-brand': 'var(--color-bg)',
  'bg-warm':  'var(--color-bg-warm)',
  soft:     'var(--color-soft)',
  primary:  { 50: 'var(--primary-50)', ... 950: 'var(--primary-950)' }  // unverändert
}
```

### Default Primary → Karmin
Der Fallback in `main.css` (aktuell Violett) wird auf eine von Karmin (`#a51f2c`) abgeleitete Skala umgestellt. Die exakten Hex-Werte werden zur Implementierungszeit mit `generatePalette('#a51f2c')` aus dem bestehenden `colorPalette.js` erzeugt. `--primary-600` = `#a51f2c`, `--primary-800` = `#6c0d18` (Bordeaux).

`applyTheme()` überschreibt diese Werte weiterhin pro Instanz — keine Änderung an `colorPalette.js`.

---

## 2. Fonts

### `index.html`
Inter entfernen, ersetzen durch:
```html
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
```

### `main.css` — Body
```css
body {
  @apply bg-bg-brand text-ink antialiased;
  font-family: var(--font-body);
  -webkit-text-size-adjust: 100%;
}
```
`font-feature-settings` für Inter entfällt.

---

## 3. SVG-Assets

Aus Repo-Root `assets/` nach `standdienst-frontend/public/assets/` kopieren:
- `mark-ticket.svg`
- `mark-ticket-mono.svg`
- `wordmark.svg`
- `favicon-ticket.svg`

`standdienst-frontend/public/favicon.svg` wird durch `favicon-ticket.svg` ersetzt.

---

## 4. Komponenten-Klassen (`main.css`)

### Buttons
```css
.btn-primary   → bg-ink text-soft hover:bg-primary-600 active:bg-primary-700
.btn-secondary → bg-soft text-ink border border-sand hover:bg-bg-warm
.btn-danger    → bleibt rot (Signalwert)
```

### Cards
```css
.card             → bg-soft border border-sand rounded-md (kein shadow-sm, kein rounded-2xl; --radius-md = 8px)
.card-interactive → wie .card + hover:shadow-sm + hover:-translate-y-0.5
```

### Inputs & Labels
```css
.input → bg-soft border-sand placeholder:text-muted
         focus:border-primary-500 focus:ring-primary-500
         disabled:bg-bg-brand disabled:text-muted
.label → text-ink font-medium (statt text-gray-700)
```

### Badges
```css
.badge-green  → bg-[#d4edda] text-ink
.badge-red    → bg-primary-50 text-primary-700
.badge-yellow → bg-[#fef3cd] text-ink
.badge-blue   → bg-[#dbeafe] text-ink
```

### Scrollbar
```css
::-webkit-scrollbar-thumb → bg-sand hover:bg-muted
```

---

## 5. Layouts

### `AdminLayout.vue`
| Element | Neu |
|---|---|
| Sidebar + Mobile Header | `bg-ink` (statt `bg-primary-950`) |
| Seiten-Hintergrund | `bg-bg-brand` (statt `bg-gray-50`) |
| Alle anderen Elemente | unverändert (weiß/10, white/35 etc. passen auf Tinte) |

### `VolunteerLayout.vue`
| Element | Neu |
|---|---|
| Header | bleibt `bg-primary-600` — Default wird Karmin durch neue CSS-Variablen |
| Mobile Bottom-Nav | `bg-soft border-sand` (statt `bg-white border-gray-200`) |

### `AppFooter.vue`
Alle `text-gray-*` → `text-muted` / `text-ink`.

---

## 6. Gray-Mapping (universell, alle Vue-Dateien)

| Alt | Neu | Semantik |
|---|---|---|
| `bg-gray-50`, `bg-gray-100` | `bg-bg-brand` | Seiten-/Abschnittshintergrund |
| `bg-white` | `bg-soft` | Karten, Inputs, Modals |
| `border-gray-100`, `border-gray-200` | `border-sand` | Trennlinien |
| `divide-gray-200` | `divide-sand` | Tabellen-Divider |
| `text-gray-900` | `text-ink` | Haupttext |
| `text-gray-700`, `text-gray-600` | `text-ink/80` | Sekundärtext |
| `text-gray-500`, `text-gray-400` | `text-muted` | Dezenter Text |
| `text-gray-300` | `text-sand` | Sehr dezenter Text |
| `bg-gray-600`, `bg-gray-700` | `bg-muted` / `bg-ink` | Dunkle Flächen |
| `hover:bg-gray-50` | `hover:bg-bg-warm` | Hover-States |
| `hover:bg-gray-100` | `hover:bg-bg-warm` | Hover-States |

**Ausnahmen (bleiben unverändert):**
- Toast-Hintergrund `bg-gray-900` (maximaler Kontrast, funktional)
- Modal-Overlay `bg-gray-500/75` (Standard-UI-Konvention)
- `btn-danger` (Rot bleibt Signalfarbe)
- Rote/grüne Ampelfarben in Tabellen (`text-green-600`, `text-red-600` etc.)

---

## 7. Spezifische View-Regeln

### Tabellen (Admin-Views)
- `thead`: `bg-bg-brand`, `text-muted`, `border-sand`
- `tbody tr hover`: `hover:bg-bg-warm`
- Mobile gestapelte Listen: `bg-bg-brand` Hintergrund, `border-sand`

### Modals & Dialoge (`Modal.vue`, `ConfirmDialog.vue`)
- Container: `bg-soft border-sand`
- Overlay: unverändert

### Login/Auth-Seiten (Admin + Volunteer)
- Seiten-Hintergrund: `bg-bg-brand`
- Login-Card: `bg-soft border-sand`

### Setup-Wizard
- Step-Indikatoren: `bg-sand` (inaktiv), `text-muted`
- Aktiver Step: `bg-primary-600` (unverändert)

### Geist Mono
Alle bestehenden `font-mono`-Klassen bleiben — Geist Mono greift automatisch über `--font-mono` aus `tokens.css`.

---

## 8. Nicht geändert

- Routing, Stores, API-Layer
- Backend
- Layout-Struktur (Grid, Flex, Größen)
- Rote/grüne Statusfarben (semantisch)
- Per-Instanz-Theming-Logik (`colorPalette.js`, `applyTheme()`)
- `btn-danger`
