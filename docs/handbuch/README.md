# Standdienst · Handbuch

Vollständiges Benutzerhandbuch für alle Rollen – als eine in sich geschlossene HTML-Datei
im Farb- und Schriftlayout der Anwendung (Papier & Karmin, Hanken Grotesk).

## Inhalt

- **`handbuch.html`** – das komplette Handbuch. Einfach im Browser öffnen.
- **`screenshots/`** – Ablageort für die echten Bildschirmfotos.

## Aufbau

Das Handbuch ist nach Nutzergruppen gegliedert:

1. **Freiwillige** – Anmelden, Schichten buchen, Essen spenden, Profil & Datenschutz
2. **Organisator:innen** – Termine, Stände, Schichten, Anmeldungs-Raster, Listen, Export/Import
3. **Instanz-Admins** – Branding, Funktionsschalter & Fristen, Impressum/Datenschutz, DSGVO
4. **Plattform-Admins** – Setup, Instanzen & Organisatoren, Mail, Backups, Updates
5. **Shell-Admins** – `install.sh`, `update.sh`, `uninstall.sh`, `.env`-Variablen

Dazu zwei Anhänge: die **Screenshot-Regie** (Klappenliste) und ein **Glossar mit FAQ**.

## Screenshots ergänzen

Das Handbuch enthält 19 gestaltete Platzhalter mit jeweils einer **Regie-Anweisung**
(welche Rolle, welche Seite, welcher Zustand). So gehst du vor:

1. Ein aufgeräumtes Demo-System mit Beispieldaten vorbereiten
   (Demo-Instanz mit Logo & Farbe, ein paar Termine/Stände/Schichten, einige Helfer).
2. Die Screenshots laut Regie aufnehmen (Browser ~1280 px Breite) und unter
   `screenshots/01.png`, `02.png`, … ablegen.
3. Im `handbuch.html` den jeweiligen Platzhalter ersetzen: den Block
   `<div class="stage">…</div>` durch
   `<img src="screenshots/03.png" alt="Schichtenübersicht" style="width:100%;display:block" />`.

Die `<figcaption>` mit der Regie kann danach entfernt oder durch eine echte Bildunterschrift
ersetzt werden.

## Als PDF weitergeben

`handbuch.html` im Browser öffnen → **Drucken → Als PDF speichern**. Das Layout ist
darauf ausgelegt, auch gedruckt sauber auszusehen.
