# Brand-Implementierung Standdienst — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die Standdienst-Brand (Karmin/Tinte/Sand, Hanken Grotesk, Geist Mono) vollständig in die Vue-3-SPA einführen — nur Styling, kein Layout-Umbau, per-Instanz-Theming bleibt erhalten.

**Architecture:** tokens.css als Single Source of Truth → in main.css importiert + Tailwind um Brand-Farbnamen erweitert. Alle `gray-*`/`white`-Klassen in Vue-Dateien werden nach dem Gray-Mapping auf Brand-Tokens umgestellt. Der Default-Primary wechselt von Violett auf Karmin; `applyTheme()` bleibt unverändert.

**Tech Stack:** Vue 3, Tailwind CSS 3, Vite, CSS Custom Properties

---

## Gray-Mapping (Referenz für alle Tasks)

| Alt | Neu | Semantik |
|---|---|---|
| `bg-gray-50`, `bg-gray-100` | `bg-bg-brand` | Seiten-/Abschnittshintergrund |
| `bg-white` | `bg-soft` | Karten, Inputs, Modals |
| `border-gray-100`, `border-gray-200`, `border-gray-300` | `border-sand` | Trennlinien |
| `divide-gray-100`, `divide-gray-200` | `divide-sand` | Tabellen-Divider |
| `text-gray-900` | `text-ink` | Haupttext |
| `text-gray-700`, `text-gray-600` | `text-ink/80` | Sekundärtext |
| `text-gray-500`, `text-gray-400` | `text-muted` | Dezenter Text |
| `text-gray-300` | `text-sand` | Sehr dezenter Text |
| `bg-gray-600`, `bg-gray-700` | `bg-muted` | Dunkle Flächen |
| `hover:bg-gray-50`, `hover:bg-gray-100` | `hover:bg-bg-warm` | Hover-States |
| `focus:ring-gray-*` | `focus:ring-primary-500` | Fokus-Ring |
| `rounded-2xl` (Cards/Modals) | `rounded-md` | Radius Brand-konform |
| `rounded-t-2xl`, `rounded-b-2xl` | `rounded-t-md`, `rounded-b-md` | Radius Brand-konform |

**Ausnahmen (nicht ändern):**
- `bg-gray-900` (Toast-Hintergrund, maximaler Kontrast)
- `bg-black/40`, `bg-gray-500/75` (Modal-Overlay)
- `text-green-*`, `text-red-*`, `bg-green-*`, `bg-red-*` (Statusfarben)
- `btn-danger` (bleibt rot)
- Klassen, die per-Instanz-Primary nutzen (`bg-primary-*`, `text-primary-*`)

---

## Task 1: Setup — Tokens, Fonts, Assets, Config

**Files:**
- Create: `standdienst-frontend/src/assets/tokens.css`
- Modify: `standdienst-frontend/index.html`
- Modify: `standdienst-frontend/tailwind.config.js`
- Modify: `standdienst-frontend/src/assets/main.css`
- Create: `standdienst-frontend/public/assets/` (Verzeichnis + 4 SVGs)
- Modify: `standdienst-frontend/public/favicon.svg`

---

- [ ] **Schritt 1.1: tokens.css nach src/assets kopieren**

```bash
cp /mnt/nc-tobi/standdienst_v2/tokens.css \
   /mnt/nc-tobi/standdienst_v2/standdienst-frontend/src/assets/tokens.css
```

---

- [ ] **Schritt 1.2: SVG-Assets nach public/assets/ kopieren**

```bash
mkdir -p /mnt/nc-tobi/standdienst_v2/standdienst-frontend/public/assets
cp /mnt/nc-tobi/standdienst_v2/assets/mark-ticket.svg \
   /mnt/nc-tobi/standdienst_v2/standdienst-frontend/public/assets/
cp /mnt/nc-tobi/standdienst_v2/assets/mark-ticket-mono.svg \
   /mnt/nc-tobi/standdienst_v2/standdienst-frontend/public/assets/
cp /mnt/nc-tobi/standdienst_v2/assets/wordmark.svg \
   /mnt/nc-tobi/standdienst_v2/standdienst-frontend/public/assets/
cp /mnt/nc-tobi/standdienst_v2/assets/favicon-ticket.svg \
   /mnt/nc-tobi/standdienst_v2/standdienst-frontend/public/favicon.svg
```

---

- [ ] **Schritt 1.3: index.html — Inter ersetzen durch Hanken Grotesk + Geist Mono**

Datei: `standdienst-frontend/index.html`

Ersetze:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
```
Durch:
```html
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
```

---

- [ ] **Schritt 1.4: tailwind.config.js — Brand-Farben ergänzen**

Datei: `standdienst-frontend/tailwind.config.js`

Vollständiger neuer Inhalt:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        ink:       'var(--color-ink)',
        muted:     'var(--color-muted)',
        sand:      'var(--color-sand)',
        'bg-brand': 'var(--color-bg)',
        'bg-warm':  'var(--color-bg-warm)',
        soft:      'var(--color-soft)',
        primary: {
          50:  'var(--primary-50)',
          100: 'var(--primary-100)',
          200: 'var(--primary-200)',
          300: 'var(--primary-300)',
          400: 'var(--primary-400)',
          500: 'var(--primary-500)',
          600: 'var(--primary-600)',
          700: 'var(--primary-700)',
          800: 'var(--primary-800)',
          900: 'var(--primary-900)',
          950: 'var(--primary-950)',
        },
      },
    },
  },
  plugins: [],
}
```

---

- [ ] **Schritt 1.5: main.css vollständig ersetzen**

Datei: `standdienst-frontend/src/assets/main.css`

Den Karmin-Default-Primary berechnen: Starte den Node-REPL oder führe diesen Einzeiler aus um die Palette zu erhalten:

```bash
cd standdienst-frontend && node -e "
function hexToHsl(hex) {
  const r=parseInt(hex.slice(1,3),16)/255,g=parseInt(hex.slice(3,5),16)/255,b=parseInt(hex.slice(5,7),16)/255
  const max=Math.max(r,g,b),min=Math.min(r,g,b),l=(max+min)/2
  if(max===min)return[0,0,l*100]
  const d=max-min,s=l>0.5?d/(2-max-min):d/(max+min)
  let h
  switch(max){case r:h=((g-b)/d+(g<b?6:0))/6;break;case g:h=((b-r)/d+2)/6;break;default:h=((r-g)/d+4)/6}
  return[h*360,s*100,l*100]
}
function hslToHex(h,s,l){
  s/=100;l/=100
  const a=s*Math.min(l,1-l)
  const f=(n)=>{const k=(n+h/30)%12;return Math.round(255*(l-a*Math.max(Math.min(k-3,9-k,1),-1))).toString(16).padStart(2,'0')}
  return '#'+f(0)+f(8)+f(4)
}
function clamp(v,lo=0,hi=100){return Math.max(lo,Math.min(hi,v))}
function generatePalette(hex){
  const[h,s,l]=hexToHsl(hex)
  const lighter=(lt,st)=>hslToHex(h,clamp(s*st),clamp(l+(97-l)*lt))
  const darker=(delta)=>hslToHex(h,clamp(s*1.05),clamp(l+delta,4))
  return{50:lighter(1.00,0.12),100:lighter(0.90,0.22),200:lighter(0.76,0.40),300:lighter(0.60,0.60),400:lighter(0.40,0.80),500:lighter(0.18,0.93),600:hex,700:darker(-9),800:darker(-20),900:darker(-33),950:darker(-45)}
}
console.log(JSON.stringify(generatePalette('#a51f2c'),null,2))
"
```

Die Ausgabe liefert die konkreten Hex-Werte für die `--primary-*`-Variablen. Setze diese Werte in den `:root`-Block in main.css ein (Beispielwerte — mit tatsächlicher Ausgabe ersetzen):

Vollständiger neuer Inhalt von `standdienst-frontend/src/assets/main.css`:

```css
@import './tokens.css';

@tailwind base;
@tailwind components;
@tailwind utilities;

/* Default-Primary: Karmin — wird zur Laufzeit durch applyTheme() pro Instanz überschrieben */
:root {
  /* Werte aus generatePalette('#a51f2c') — mit Skript in Schritt 1.5 berechnen */
  --primary-50:  <WERT_AUS_SKRIPT>;
  --primary-100: <WERT_AUS_SKRIPT>;
  --primary-200: <WERT_AUS_SKRIPT>;
  --primary-300: <WERT_AUS_SKRIPT>;
  --primary-400: <WERT_AUS_SKRIPT>;
  --primary-500: <WERT_AUS_SKRIPT>;
  --primary-600: #a51f2c;
  --primary-700: <WERT_AUS_SKRIPT>;
  --primary-800: #6c0d18;
  --primary-900: <WERT_AUS_SKRIPT>;
  --primary-950: <WERT_AUS_SKRIPT>;
}

@layer base {
  body {
    @apply bg-bg-brand text-ink antialiased;
    font-family: var(--font-body);
    -webkit-text-size-adjust: 100%;
  }

  html, body {
    overscroll-behavior: none;
  }
  body {
    overflow-x: hidden;
  }

  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { @apply bg-sand rounded-full; }
  ::-webkit-scrollbar-thumb:hover { @apply bg-muted; }
}

@layer utilities {
  .pb-safe {
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }
  .mb-safe {
    margin-bottom: env(safe-area-inset-bottom, 0px);
  }
  .scroll-pb-nav {
    scroll-padding-bottom: calc(5rem + env(safe-area-inset-bottom, 0px));
  }
}

@layer components {
  /* ── Buttons ─────────────────────────────────────────────────── */
  .btn {
    @apply inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium text-sm
           cursor-pointer select-none
           transition-all duration-150 ease-out
           disabled:opacity-50 disabled:cursor-not-allowed
           active:scale-[0.97];
  }
  .btn-primary {
    @apply btn bg-ink text-soft hover:bg-primary-600 active:bg-primary-700
           focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2;
  }
  .btn-secondary {
    @apply btn bg-soft text-ink border border-sand hover:bg-bg-warm
           focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2;
  }
  .btn-danger {
    @apply btn bg-red-600 text-white hover:bg-red-700
           focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2;
  }

  /* ── Inputs ─────────────────────────────────────────────────── */
  .input {
    @apply block w-full rounded-lg border border-sand bg-soft px-3 py-2.5 text-[16px] md:text-sm
           text-ink placeholder:text-muted
           transition-colors duration-150
           focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-0
           disabled:bg-bg-brand disabled:text-muted disabled:cursor-not-allowed;
  }
  .label {
    @apply block text-sm font-medium text-ink/80 mb-1.5;
  }

  /* ── Cards ──────────────────────────────────────────────────── */
  .card {
    @apply bg-soft rounded-md border border-sand p-4 lg:p-6;
  }

  .card-interactive {
    @apply card cursor-pointer
           transition-all duration-150 ease-out
           hover:shadow-sm hover:-translate-y-0.5
           active:scale-[0.99] active:shadow-none active:translate-y-0
           focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2;
  }

  /* ── Badges ─────────────────────────────────────────────────── */
  .badge {
    @apply inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium;
  }
  .badge-green  { @apply badge bg-[#d4edda]  text-ink; }
  .badge-red    { @apply badge bg-primary-50 text-primary-700; }
  .badge-yellow { @apply badge bg-[#fef3cd]  text-ink; }
  .badge-blue   { @apply badge bg-[#dbeafe]  text-ink; }
}
```

---

- [ ] **Schritt 1.6: Dev-Server starten und Basis verifizieren**

```bash
cd standdienst-frontend && npm run dev
```

Öffne http://localhost:5173 und prüfe:
- Body-Hintergrund ist warmes Papier (#f5ece1), nicht mehr grau
- Font ist Hanken Grotesk (in DevTools → Elements → Computed → font-family prüfen)
- Favicon im Browser-Tab zeigt Ticket-Icon

---

- [ ] **Schritt 1.7: Committen**

```bash
cd standdienst-frontend && git add src/assets/tokens.css src/assets/main.css public/assets/ public/favicon.svg ../index.html ../tailwind.config.js
git commit -m "feat: Brand-Setup — Tokens, Fonts, Assets, Tailwind-Konfiguration"
```

---

## Task 2: Layouts — AdminLayout, VolunteerLayout, AppFooter

**Files:**
- Modify: `standdienst-frontend/src/layouts/AdminLayout.vue`
- Modify: `standdienst-frontend/src/layouts/VolunteerLayout.vue`
- Modify: `standdienst-frontend/src/components/AppFooter.vue`

---

- [ ] **Schritt 2.1: AdminLayout.vue — Sidebar und Hintergrund**

Datei: `standdienst-frontend/src/layouts/AdminLayout.vue`

Lese die vollständige Datei und ersetze alle Vorkommen:

| Suchen | Ersetzen |
|---|---|
| `bg-primary-950` | `bg-ink` |
| `bg-gray-50` | `bg-bg-brand` |

`bg-primary-950` erscheint in Sidebar und Mobile Header; prüfe ob noch weitere Vorkommen (z. B. Mobile Bottom Nav) existieren. `bg-gray-50` erscheint im Haupt-Wrapper `<div class="min-h-screen bg-gray-50 flex...">`.

Wende danach das vollständige Gray-Mapping auf alle weiteren `gray-*`/`white`-Klassen im Template-Teil an (Script-Teil bleibt unverändert).

---

- [ ] **Schritt 2.2: VolunteerLayout.vue — Mobile Bottom Nav**

Datei: `standdienst-frontend/src/layouts/VolunteerLayout.vue`

Ersetze im Mobile Bottom Nav `<nav>`:
```html
class="lg:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 z-40"
```
Durch:
```html
class="lg:hidden fixed bottom-0 inset-x-0 bg-soft border-t border-sand z-40"
```

Der Header (`bg-primary-600`) bleibt unverändert — er nimmt automatisch Karmin als Default.

---

- [ ] **Schritt 2.3: AppFooter.vue lesen und grays ersetzen**

Lese die Datei und ersetze alle `gray-*` nach dem Gray-Mapping. Typische Muster:
- `text-gray-500` → `text-muted`
- `text-gray-400` → `text-muted`
- `text-gray-900` → `text-ink`
- `border-gray-200` → `border-sand`
- `bg-gray-50` → `bg-bg-brand`

---

- [ ] **Schritt 2.4: Visuell prüfen**

Im laufenden Dev-Server prüfen:
- Admin-Sidebar: tiefes Tinte-Schwarz (#1a1311) statt Violett
- Admin-Hauptbereich: warmer Papier-Hintergrund
- Volunteer Mobile Bottom-Nav: Soft-Cream Hintergrund mit Sand-Rahmen

---

- [ ] **Schritt 2.5: Committen**

```bash
git add standdienst-frontend/src/layouts/ standdienst-frontend/src/components/AppFooter.vue
git commit -m "feat: Brand — Layouts und Footer"
```

---

## Task 3: Shared Components

**Files:**
- Modify: `standdienst-frontend/src/components/Modal.vue`
- Modify: `standdienst-frontend/src/components/ConfirmDialog.vue`
- Modify: `standdienst-frontend/src/components/Pagination.vue`
- Modify: `standdienst-frontend/src/components/SortTh.vue`
- Modify: `standdienst-frontend/src/components/LoadingSpinner.vue`
- Modify: `standdienst-frontend/src/components/ToastContainer.vue`

---

- [ ] **Schritt 3.1: Modal.vue**

Datei: `standdienst-frontend/src/components/Modal.vue`

Ersetze:
```html
class="relative bg-white rounded-2xl shadow-2xl w-full max-h-[90vh] overflow-y-auto"
```
Durch:
```html
class="relative bg-soft rounded-md border border-sand shadow-lg w-full max-h-[90vh] overflow-y-auto"
```

Ersetze:
```html
class="flex items-center justify-between p-6 border-b border-gray-100"
```
Durch:
```html
class="flex items-center justify-between p-6 border-b border-sand"
```

Ersetze:
```html
class="text-lg font-semibold text-gray-900"
```
Durch:
```html
class="text-lg font-semibold text-ink"
```

Ersetze:
```html
class="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
```
Durch:
```html
class="p-1 rounded-lg text-muted hover:text-ink hover:bg-bg-warm transition-colors"
```

---

- [ ] **Schritt 3.2: ConfirmDialog.vue**

Datei: `standdienst-frontend/src/components/ConfirmDialog.vue`

Ersetze:
```html
<p class="text-gray-600 mb-6">
```
Durch:
```html
<p class="text-ink/80 mb-6">
```

---

- [ ] **Schritt 3.3: Pagination.vue, SortTh.vue, LoadingSpinner.vue, ToastContainer.vue**

Lese jede Datei und wende das Gray-Mapping an. Wichtige Ausnahme: In `ToastContainer.vue` bleibt `bg-gray-900` (oder entsprechendes) für den Toast-Hintergrund erhalten.

Typische Muster in `Pagination.vue`:
- `bg-white` → `bg-soft`
- `border-gray-300` → `border-sand`
- `text-gray-500` → `text-muted`
- `text-gray-700` → `text-ink/80`
- `hover:bg-gray-50` → `hover:bg-bg-warm`
- `disabled:text-gray-300` → `disabled:text-sand`

Typische Muster in `SortTh.vue`:
- `text-gray-500` → `text-muted`
- `hover:text-gray-700` → `hover:text-ink/80`

---

- [ ] **Schritt 3.4: Visuell prüfen**

Öffne eine Admin-Seite mit einer Tabelle und klicke auf "Erstellen" um ein Modal zu öffnen.
- Modal: Soft-Cream Hintergrund, Sand-Rahmen
- ConfirmDialog: korrekte Textfarbe

---

- [ ] **Schritt 3.5: Committen**

```bash
git add standdienst-frontend/src/components/
git commit -m "feat: Brand — Shared Components"
```

---

## Task 4: Volunteer Views

**Files:**
- Modify: `standdienst-frontend/src/views/volunteer/Login.vue`
- Modify: `standdienst-frontend/src/views/volunteer/Register.vue`
- Modify: `standdienst-frontend/src/views/volunteer/WelcomeSetup.vue`
- Modify: `standdienst-frontend/src/views/volunteer/ForgotPassword.vue`
- Modify: `standdienst-frontend/src/views/volunteer/ResetPassword.vue`
- Modify: `standdienst-frontend/src/views/volunteer/Home.vue`
- Modify: `standdienst-frontend/src/views/volunteer/Shifts.vue`
- Modify: `standdienst-frontend/src/views/volunteer/MyShifts.vue`
- Modify: `standdienst-frontend/src/views/volunteer/FoodDonations.vue`
- Modify: `standdienst-frontend/src/views/volunteer/Profile.vue`

---

- [ ] **Schritt 4.1: Auth-Views (Login, Register, WelcomeSetup, ForgotPassword, ResetPassword)**

Diese Views haben Login-Cards-Muster: Seite in `bg-gray-50/100`, Card in `bg-white`.

Wende das Gray-Mapping auf alle 5 Dateien an. Repräsentatives Beispiel aus `volunteer/Login.vue`:

```html
<!-- Alt -->
<div class="min-h-screen bg-gray-50 flex items-center justify-center px-4">
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 w-full max-w-md">
    <h1 class="text-2xl font-bold text-gray-900 mb-1">Anmelden</h1>
    <p class="text-gray-500 text-sm mb-6">...</p>

<!-- Neu -->
<div class="min-h-screen bg-bg-brand flex items-center justify-center px-4">
  <div class="bg-soft rounded-md border border-sand p-8 w-full max-w-md">
    <h1 class="text-2xl font-bold text-ink mb-1">Anmelden</h1>
    <p class="text-muted text-sm mb-6">...</p>
```

Wende dasselbe Muster auf alle 5 Auth-Views an.

---

- [ ] **Schritt 4.2: Shifts.vue**

Datei: `standdienst-frontend/src/views/volunteer/Shifts.vue`

Ersetze alle gray-Klassen nach dem Mapping. Besondere Stellen:

```html
<!-- Sticky Datumsheader -->
<!-- Alt -->
class="sticky top-14 z-10 -mx-4 px-4 py-2 bg-gray-50 border-b border-gray-200"
<!-- Neu -->
class="sticky top-14 z-10 -mx-4 px-4 py-2 bg-bg-brand border-b border-sand"

<!-- Alt: Datumstext -->
class="text-sm font-bold uppercase tracking-wide text-gray-500"
<!-- Neu -->
class="text-sm font-bold uppercase tracking-wide text-muted"

<!-- Sticky Kartenheader -->
<!-- Alt -->
class="sticky top-[5.75rem] z-[9] -mx-4 px-4 bg-gray-50"
<!-- Neu -->
class="sticky top-[5.75rem] z-[9] -mx-4 px-4 bg-bg-brand"

<!-- Stand-Card Header (weißer Teil) -->
<!-- Alt -->
class="bg-white px-4 py-2 flex items-center justify-between"
<!-- Neu -->
class="bg-soft px-4 py-2 flex items-center justify-between"

<!-- Alt: "Alle voll" Text -->
class="text-xs text-gray-400 font-medium"
<!-- Neu -->
class="text-xs text-muted font-medium"

<!-- Kartenkörper -->
<!-- Alt -->
class="bg-white rounded-b-2xl border border-t-0 border-gray-100 p-4"
<!-- Neu -->
class="bg-soft rounded-b-md border border-t-0 border-sand p-4"

<!-- Nicht eingetragene, nicht volle Schicht -->
<!-- Alt -->
'border-gray-100': !shift.is_registered && !shift.is_full,
<!-- Neu -->
'border-sand': !shift.is_registered && !shift.is_full,

<!-- Volle Schicht -->
<!-- Alt -->
'border-gray-100 bg-gray-50/40 opacity-50': !shift.is_registered && shift.is_full,
<!-- Neu -->
'border-sand bg-bg-brand/40 opacity-50': !shift.is_registered && shift.is_full,

<!-- Progress Bar Hintergrund -->
<!-- Alt -->
class="h-1.5 bg-gray-200 rounded-full w-24"
<!-- Neu -->
class="h-1.5 bg-sand rounded-full w-24"

<!-- Namens-Chips -->
<!-- Alt -->
class="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded"
<!-- Neu -->
class="text-xs bg-bg-warm text-ink/80 px-1.5 py-0.5 rounded"

<!-- Skeleton-Animationen -->
<!-- Alt -->
class="... bg-gray-200 ..."  und  class="... bg-gray-100 ..."
<!-- Neu -->
class="... bg-sand ..."      und  class="... bg-bg-warm ..."
```

---

- [ ] **Schritt 4.3: MyShifts.vue, FoodDonations.vue, Profile.vue, Home.vue**

Lese jede Datei und wende das Gray-Mapping vollständig an. Häufige Muster in diesen Views:
- Sektions-Header: `text-gray-500` → `text-muted`
- Karten-Trennlinien: `border-gray-100` → `border-sand`
- Tabellen/Listen: `bg-gray-50` Zebrastreifen → `bg-bg-warm`
- Formular-Beschreibungen: `text-gray-400` → `text-muted`
- Leere-Zustände: `text-gray-400` → `text-muted`
- Zähler / Badges: `bg-gray-100 text-gray-600` → `bg-bg-warm text-ink/80`

---

- [ ] **Schritt 4.4: Visuell prüfen**

Navigiere durch alle Volunteer-Seiten im Dev-Server:
- `/:slug/login` — Card in Soft-Cream, kein grauer Hintergrund mehr
- `/:slug/shifts` — Sticky-Headers in Papier, Karten in Cream mit Sand-Rand
- `/:slug/my-shifts` — einheitliche Palette
- `/:slug/food` — einheitliche Palette
- `/:slug/profile` — einheitliche Palette

---

- [ ] **Schritt 4.5: Committen**

```bash
git add standdienst-frontend/src/views/volunteer/
git commit -m "feat: Brand — Volunteer Views"
```

---

## Task 5: Admin Auth Views

**Files:**
- Modify: `standdienst-frontend/src/views/admin/Login.vue`
- Modify: `standdienst-frontend/src/views/admin/ForgotPassword.vue`
- Modify: `standdienst-frontend/src/views/admin/ResetPassword.vue`
- Modify: `standdienst-frontend/src/views/admin/TwoFASetup.vue`
- Modify: `standdienst-frontend/src/views/admin/TwoFAVerify.vue`

---

- [ ] **Schritt 5.1: Alle 5 Admin-Auth-Views**

Gleiche Muster wie Volunteer Auth-Views in Schritt 4.1. Wende das Gray-Mapping auf alle 5 Dateien an:
- Seiten-Hintergrund: `bg-gray-50` / `bg-gray-100` → `bg-bg-brand`
- Login-Cards: `bg-white` → `bg-soft`, `border-gray-100` → `border-sand`, `rounded-2xl` → `rounded-md`
- Texte: `text-gray-900` → `text-ink`, `text-gray-500` → `text-muted`
- QR-Code-Bereich (TwoFASetup): `bg-gray-50 border-gray-200` → `bg-bg-brand border-sand`
- Backup-Code-Liste (TwoFASetup): `bg-gray-900 text-white` bleibt (technische Darstellung)

---

- [ ] **Schritt 5.2: Visuell prüfen**

Navigiere zu `/admin/login` — kein grauer Hintergrund mehr.

---

- [ ] **Schritt 5.3: Committen**

```bash
git add standdienst-frontend/src/views/admin/Login.vue \
        standdienst-frontend/src/views/admin/ForgotPassword.vue \
        standdienst-frontend/src/views/admin/ResetPassword.vue \
        standdienst-frontend/src/views/admin/TwoFASetup.vue \
        standdienst-frontend/src/views/admin/TwoFAVerify.vue
git commit -m "feat: Brand — Admin Auth Views"
```

---

## Task 6: Admin Core CRUD Views

**Files:**
- Modify: `standdienst-frontend/src/views/admin/Dashboard.vue`
- Modify: `standdienst-frontend/src/views/admin/Volunteers.vue`
- Modify: `standdienst-frontend/src/views/admin/VolunteerDetail.vue`
- Modify: `standdienst-frontend/src/views/admin/Stands.vue`
- Modify: `standdienst-frontend/src/views/admin/Dates.vue`
- Modify: `standdienst-frontend/src/views/admin/Shifts.vue`
- Modify: `standdienst-frontend/src/views/admin/Registrations.vue`
- Modify: `standdienst-frontend/src/views/admin/Food.vue`

---

- [ ] **Schritt 6.1: Repräsentatives Beispiel — Volunteers.vue**

Datei: `standdienst-frontend/src/views/admin/Volunteers.vue`

Ersetze nach Gray-Mapping. Tabellenspezifische Muster:

```html
<!-- Thead -->
<!-- Alt -->
<thead class="bg-gray-50 border-b border-gray-100">
<!-- Neu -->
<thead class="bg-bg-brand border-b border-sand">

<!-- Thead-Texte -->
<!-- In SortTh: text-gray-500 → text-muted (via SortTh bereits gefixt in Task 3) -->

<!-- Tbody-Zeilen -->
<!-- Alt -->
class="border-b border-gray-50 hover:bg-gray-50"
<!-- Neu -->
class="border-b border-sand hover:bg-bg-warm"

<!-- Zellen-Texte -->
<!-- Alt -->
class="px-4 py-3 text-gray-500"
<!-- Neu -->
class="px-4 py-3 text-muted"

<!-- Mobile Liste Divider -->
<!-- Alt -->
class="md:hidden divide-y divide-gray-50"
<!-- Neu -->
class="md:hidden divide-y divide-sand"

<!-- Mobile Subtexte -->
<!-- Alt -->
class="text-xs text-gray-500"  und  class="text-gray-200"
<!-- Neu -->
class="text-xs text-muted"    und  class="text-sand"

<!-- Leere Zustände -->
<!-- Alt -->
class="px-4 py-8 text-center text-gray-400 text-sm"
<!-- Neu -->
class="px-4 py-8 text-center text-muted text-sm"
```

---

- [ ] **Schritt 6.2: Remaining 7 Views**

Wende das gleiche Muster auf Dashboard.vue, VolunteerDetail.vue, Stands.vue, Dates.vue, admin/Shifts.vue, Registrations.vue, Food.vue an.

Zusätzliche Dashboard-Muster:
- Statistik-Karten: `bg-white` → `bg-soft`, `border-gray-100` → `border-sand`
- Kicker-Texte: `text-gray-400` → `text-muted`

Zusätzliche VolunteerDetail-Muster:
- Zurück-Button: `text-gray-500 hover:text-gray-700` → `text-muted hover:text-ink/80`
- Schicht/Spenden-Timeline: `border-gray-100` → `border-sand`

---

- [ ] **Schritt 6.3: Visuell prüfen**

- Admin-Helfer-Liste: Tabelle in Soft-Cream, Sand-Trennlinien, kein grauer Thead
- Admin-Dashboard: Statistik-Karten in Cream
- Admin-Schichten: konsistente Palette

---

- [ ] **Schritt 6.4: Committen**

```bash
git add standdienst-frontend/src/views/admin/Dashboard.vue \
        standdienst-frontend/src/views/admin/Volunteers.vue \
        standdienst-frontend/src/views/admin/VolunteerDetail.vue \
        standdienst-frontend/src/views/admin/Stands.vue \
        standdienst-frontend/src/views/admin/Dates.vue \
        standdienst-frontend/src/views/admin/Shifts.vue \
        standdienst-frontend/src/views/admin/Registrations.vue \
        standdienst-frontend/src/views/admin/Food.vue
git commit -m "feat: Brand — Admin Core Views"
```

---

## Task 7: Admin Secondary Views

**Files:**
- Modify: `standdienst-frontend/src/views/admin/Export.vue`
- Modify: `standdienst-frontend/src/views/admin/Import.vue`
- Modify: `standdienst-frontend/src/views/admin/ActivityLog.vue`
- Modify: `standdienst-frontend/src/views/admin/InstanceActivity.vue`
- Modify: `standdienst-frontend/src/views/admin/Admins.vue`
- Modify: `standdienst-frontend/src/views/admin/Organizers.vue`
- Modify: `standdienst-frontend/src/views/admin/Instances.vue`
- Modify: `standdienst-frontend/src/views/admin/AdminProfile.vue`
- Modify: `standdienst-frontend/src/views/admin/PasskeySettings.vue`
- Modify: `standdienst-frontend/src/views/admin/Backup.vue`
- Modify: `standdienst-frontend/src/views/admin/Update.vue`
- Modify: `standdienst-frontend/src/views/admin/settings/Global.vue`
- Modify: `standdienst-frontend/src/views/admin/settings/Instance.vue`
- Modify: `standdienst-frontend/src/views/admin/settings/Mail.vue`

---

- [ ] **Schritt 7.1: Alle 14 Views**

Wende das Gray-Mapping auf alle 14 Dateien an. Die gleichen Tabellen- und Card-Muster wie in Task 6.

Besondere Muster:

**ActivityLog.vue / InstanceActivity.vue:**
- Log-Eintrags-Hintergrund: `bg-gray-50` → `bg-bg-brand`
- Zeitstempel: `text-gray-400` → `text-muted`
- Log-Level-Chips: sofern `bg-gray-100` → `bg-bg-warm`

**AdminProfile.vue / PasskeySettings.vue:**
- Abschnittshintergrund: `bg-gray-50` → `bg-bg-brand`
- Passkey-Liste: `bg-white border-gray-200` → `bg-soft border-sand`

**Backup.vue / Update.vue:**
- Info-Boxen: `bg-gray-50 border-gray-200` → `bg-bg-brand border-sand`
- Code-Blöcke: `bg-gray-900` bleibt (technische Darstellung)

**settings/Instance.vue:**
- Farb-Picker-Umgebung: `bg-gray-50` → `bg-bg-brand`
- Formular-Sections: `border-gray-200` → `border-sand`

---

- [ ] **Schritt 7.2: Visuell prüfen**

Prüfe mindestens: ActivityLog, AdminProfile, und eine Settings-Seite.

---

- [ ] **Schritt 7.3: Committen**

```bash
git add standdienst-frontend/src/views/admin/
git commit -m "feat: Brand — Admin Secondary Views"
```

---

## Task 8: Public Views + Setup + NotFound

**Files:**
- Modify: `standdienst-frontend/src/views/public/Landing.vue`
- Modify: `standdienst-frontend/src/views/public/Impressum.vue`
- Modify: `standdienst-frontend/src/views/public/PrivacyPolicy.vue`
- Modify: `standdienst-frontend/src/views/setup/SetupWizard.vue`
- Modify: `standdienst-frontend/src/views/NotFound.vue`

---

- [ ] **Schritt 8.1: Public Views (Landing, Impressum, PrivacyPolicy)**

Gray-Mapping anwenden. Landing.vue hat ggf. Hero-Abschnitte mit eigenem Hintergrund — diese auf `bg-bg-brand` / `bg-bg-warm` / `bg-soft` je nach gewünschter Hierarchie abbilden.

---

- [ ] **Schritt 8.2: SetupWizard.vue**

Wende Gray-Mapping an. Besondere Stellen:

```html
<!-- Step-Indikator inaktiv -->
<!-- Alt -->
class="... bg-gray-200 text-gray-500 ..."
<!-- Neu -->
class="... bg-sand text-muted ..."

<!-- Aktiver Step bleibt -->
class="... bg-primary-600 text-white ..."

<!-- Fortschrittsbalken -->
<!-- Alt -->
class="... bg-gray-200 ..."
<!-- Neu -->
class="... bg-sand ..."
```

---

- [ ] **Schritt 8.3: NotFound.vue**

Gray-Mapping anwenden:
- `text-gray-400` → `text-muted`
- `text-gray-900` → `text-ink`
- `bg-gray-50` → `bg-bg-brand`

---

- [ ] **Schritt 8.4: Visuell prüfen**

- Navigiere zu `/setup` (falls setup_complete=False)
- Navigiere zu einer nicht existenten Route
- Prüfe die Landing-Page falls vorhanden

---

- [ ] **Schritt 8.5: Committen**

```bash
git add standdienst-frontend/src/views/public/ \
        standdienst-frontend/src/views/setup/ \
        standdienst-frontend/src/views/NotFound.vue
git commit -m "feat: Brand — Public, Setup und NotFound Views"
```

---

## Task 9: Abschluss — Vollständige Prüfung und Release

---

- [ ] **Schritt 9.1: Build prüfen**

```bash
cd standdienst-frontend && npm run build
```

Erwartet: Build erfolgreich, keine CSS-Fehler. Warnings über unbekannte Tailwind-Klassen sind ein Hinweis auf Tippfehler im Gray-Mapping → Fehler beheben.

---

- [ ] **Schritt 9.2: Grep auf verbleibende gray-Klassen**

```bash
grep -r "bg-gray\|text-gray\|border-gray\|divide-gray\|hover:bg-gray\|ring-gray\|from-gray\|to-gray" \
  standdienst-frontend/src/views/ standdienst-frontend/src/components/ \
  standdienst-frontend/src/layouts/ | grep -v "gray-900\|gray-500/75\|gray-400/\|node_modules"
```

Jede Zeile in der Ausgabe ist ein verbleibender `gray-*` der gemappt werden muss. Exceptions:
- `bg-gray-900` in ToastContainer → absichtlich beibehalten
- `bg-gray-500/75` als Modal-Overlay → absichtlich beibehalten

---

- [ ] **Schritt 9.3: Visuelle Gesamtprüfung**

Öffne den Build (`npm run preview`) und prüfe die goldenen Pfade:

1. `/admin/login` → warmer Hintergrund, Tinte-Card
2. Admin-Sidebar → Tinte-Schwarz, kein Violett
3. Admin-Helfer-Tabelle → Sand-Trennlinien, Cream-Thead
4. Modal öffnen → Cream-Hintergrund, Sand-Rand
5. Volunteer-Login → Papier-Hintergrund
6. Volunteer-Shifts → Sticky-Header in Papier, Karten in Cream
7. Default-Primary ist Karmin (Buttons, aktive Nav-Links)
8. Per-Instanz-Farbe überschreibt korrekt (Instanz mit anderem primary_color testen)

---

- [ ] **Schritt 9.4: Version und Release**

Gemäß CLAUDE.md ist nach `feat/`-Branches ein Release Pflicht.

```bash
# version.py anpassen
# standdienst-api/version.py: VERSION = "X.Y.Z", VERSION_DATE = "2026-05-25"

git add standdienst-api/version.py
git commit -m "chore: version bump X.Y.Z"

git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z --title "vX.Y.Z — Brand-Implementierung" \
  --notes "Vollständige Einführung der Standdienst-Marke: Hanken Grotesk, Geist Mono, Karmin/Tinte/Sand-Palette, Ticket-Favicon. Beide Bereiche (Admin + Volunteer) überarbeitet. Per-Instanz-Theming bleibt erhalten."
```
