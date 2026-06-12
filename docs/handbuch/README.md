# Standdienst · Handbuch

Vollständiges Benutzerhandbuch für alle Rollen – als eine in sich geschlossene HTML-Datei
im Farb- und Schriftlayout der Anwendung (Papier & Karmin, Hanken Grotesk), mit echten
Screenshots.

## Inhalt

- **`handbuch.html`** – das komplette Handbuch. Einfach im Browser öffnen.
- **`screenshots/`** – die eingebetteten Bildschirmfotos (`01.png` … `18.png`, plus `07b.png` und `15b.png`).

## Aufbau

Das Handbuch ist nach Nutzergruppen gegliedert:

1. **Freiwillige** – Anmelden, Schichten buchen, Essen spenden, Profil & Datenschutz
2. **Organisator:innen** – Termine, Stände, Schichten, Anmeldungs-Raster, Listen, Export/Import
3. **Instanz-Admins** – Branding, Funktionsschalter & Fristen, Impressum/Datenschutz, DSGVO
4. **Plattform-Admins** – Setup, Instanzen & Organisatoren, Mail, Backups, Updates
5. **Shell-Admins** – `install.sh`, `update.sh`, `uninstall.sh`, `.env`-Variablen

Dazu zwei Anhänge: das **Abbildungsverzeichnis** und ein **Glossar mit FAQ**.

## Screenshots

Die Bilder stammen aus einer Demo-Instanz „Stadtfest Musterstadt“ (grünes Branding); die
Plattform-Ansichten erscheinen im Standard-Karminrot. Einzige Ausnahme ist die
Terminal-Ansicht (Nr. 19) im Technik-Kapitel – sie ist als gestaltete Vorschau angelegt,
weil sich ein echter Server-Installationslauf nicht sinnvoll abbilden lässt.

### Bilder neu erzeugen

Falls sich die Oberfläche ändert, lassen sich die Screenshots reproduzieren: ein Backend
mit Demo-Daten starten (SQLite genügt), pro Rolle einloggen und die Seiten bei ~1280 px
Breite aufnehmen, dann als `screenshots/NN.png` ablegen. Die Einbettung im `handbuch.html`
erfolgt über `<img class="real" src="screenshots/NN.png" …>`.

## Als PDF weitergeben

`handbuch.html` im Browser öffnen → **Drucken → Als PDF speichern**. Das Layout ist
darauf ausgelegt, auch gedruckt sauber auszusehen.
