<template>
  <div>
    <h1 class="text-2xl font-bold text-ink mb-6">Globale Einstellungen</h1>

    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <form v-else @submit.prevent="save" class="space-y-6 max-w-2xl">
      <div class="card space-y-4">
        <div>
          <label class="label">Basis-URL</label>
          <input v-model="form.base_url" class="input" placeholder="https://example.com" />
        </div>
        <div>
          <label class="label">Copyright-Text</label>
          <input v-model="form.copyright_text" class="input" />
        </div>
        <div>
          <label class="label">Zeitzone</label>
          <select v-model="form.timezone" class="input">
            <option v-for="tz in timezones" :key="tz" :value="tz">{{ tz }}</option>
          </select>
        </div>
        <div>
          <label class="label">Log-Aufbewahrung (Monate)</label>
          <input v-model.number="form.log_retention_months" type="number" min="1" max="60" class="input max-w-xs" />
        </div>
        <div>
          <label class="label">Volunteer-Aufbewahrung nach Löschung (Monate)</label>
          <input v-model.number="form.volunteer_retention_months" type="number" min="1" max="120"
                 class="input max-w-xs" placeholder="Leer = deaktiviert" />
          <p class="text-xs text-muted mt-1">
            Soft-gelöschte Volunteers werden nach dieser Frist automatisch permanent gelöscht.
          </p>
        </div>
      </div>

      <div class="card space-y-4">
        <h2 class="text-base font-semibold text-ink">Sicherheit</h2>
        <div>
          <label class="label">IP-Whitelist (Rate-Limit + Fail2Ban ausgenommen)</label>
          <textarea
            v-model="form.ip_whitelist"
            class="input font-mono text-sm"
            rows="3"
            placeholder="Eine IP oder CIDR pro Zeile, z.B.: 192.168.1.0/24, 10.0.0.1"
            @blur="normalizeWhitelist"
          />
          <p class="text-xs text-muted mt-1">
            Komma- oder zeilengetrennte IPv4/IPv6-Adressen oder CIDR-Ranges.
            Diese IPs sind von Rate-Limits und Fail2Ban-Logging ausgenommen.
          </p>
        </div>
      </div>

      <div class="card space-y-4">
        <h2 class="text-base font-semibold text-ink">GitHub / Updates</h2>
        <div>
          <label class="label">GitHub-Repository</label>
          <input v-model="form.github_repo" class="input font-mono text-sm"
                 placeholder="owner/repo  z.B. toke7919/standdienst_v2" />
          <p class="text-xs text-muted mt-1">
            Wird für den Update-Check benötigt. Format: <code class="bg-bg-brand px-1 rounded">owner/repo</code>
          </p>
        </div>
        <div>
          <label class="label">GitHub Personal Access Token (PAT)</label>
          <input v-model="form.github_pat" type="password" class="input font-mono text-sm"
                 placeholder="ghp_xxxxxxxxxxxxxxxxxxxx" autocomplete="off" />
          <p class="text-xs text-muted mt-1">Optional – erhöht das API-Limit für private Repos.</p>
        </div>
      </div>

      <div class="card space-y-4">
        <h2 class="text-base font-semibold text-ink">Kontaktdaten Plattformbetreiber</h2>
        <p class="text-xs text-muted -mt-2" v-pre>
          Diese Daten werden als Platzhalter <code class="bg-bg-brand px-1 rounded">{{organisation}}</code> usw. in die Vorlagen eingesetzt, wenn Impressum/Datenschutz ohne Instanz-Kontext (/impressum) aufgerufen wird.
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="label">Organisation / Verein</label>
            <input v-model="form.contact_organisation" class="input" placeholder="Musterverein e.V." />
          </div>
          <div>
            <label class="label">Verantwortliche Person</label>
            <input v-model="form.contact_person" class="input" placeholder="Max Mustermann" />
          </div>
          <div>
            <label class="label">Straße &amp; Hausnummer</label>
            <input v-model="form.contact_street" class="input" placeholder="Musterstraße 1" />
          </div>
          <div>
            <label class="label">PLZ &amp; Ort</label>
            <input v-model="form.contact_zip_city" class="input" placeholder="12345 Musterstadt" />
          </div>
          <div>
            <label class="label">E-Mail</label>
            <input v-model="form.contact_email" class="input" type="email" placeholder="kontakt@beispiel.de" />
          </div>
          <div>
            <label class="label">Telefon</label>
            <input v-model="form.contact_phone" class="input" type="tel" placeholder="+49 123 456789" />
          </div>
        </div>
      </div>

      <div class="card space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-base font-semibold text-ink">Impressum-Vorlage (HTML)</h2>
            <p class="text-xs text-muted mt-0.5" v-pre>
              Platzhalter: <code class="bg-bg-brand px-1 rounded">{{organisation}}</code>
              <code class="bg-bg-brand px-1 rounded ml-1">{{person}}</code>
              <code class="bg-bg-brand px-1 rounded ml-1">{{adresse}}</code>
              <code class="bg-bg-brand px-1 rounded ml-1">{{plz_ort}}</code>
              <code class="bg-bg-brand px-1 rounded ml-1">{{email}}</code>
              <code class="bg-bg-brand px-1 rounded ml-1">{{telefon}}</code>
            </p>
          </div>
          <button type="button" class="btn-secondary text-xs py-1 px-2 flex-shrink-0"
                  @click="form.impressum_template_html = impressumVorlage">
            Vorlage
          </button>
        </div>
        <textarea v-model="form.impressum_template_html" class="input font-mono text-xs" rows="12"
                  placeholder="HTML-Vorlage für das Impressum (§ 5 TMG)" />
      </div>

      <div class="card space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-base font-semibold text-ink">Datenschutz-Vorlage (HTML)</h2>
            <p class="text-xs text-muted mt-0.5">Gleiche Platzhalter wie Impressum-Vorlage.</p>
          </div>
          <button type="button" class="btn-secondary text-xs py-1 px-2 flex-shrink-0"
                  @click="form.datenschutz_template_html = datenschutzVorlage">
            Vorlage
          </button>
        </div>
        <textarea v-model="form.datenschutz_template_html" class="input font-mono text-xs" rows="14"
                  placeholder="HTML-Vorlage für die Datenschutzerklärung (Art. 13 DSGVO)" />
      </div>

      <div class="card">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-base font-semibold text-ink">Betreiber-Impressum (HTML)</h2>
          <button type="button" class="btn-secondary text-xs py-1 px-2"
                  @click="form.provider_impressum_html = legacyImpressumTemplate">
            Vorlage einfügen
          </button>
        </div>
        <p class="text-xs text-muted mb-3">Wird als "Technischer Betreiber"-Abschnitt unter instanzspezifischen Impressumsseiten angehängt.</p>
        <textarea v-model="form.provider_impressum_html" class="input font-mono text-xs" rows="10"
                  placeholder="HTML für das Betreiber-Impressum (§ 5 TMG)" />
      </div>

      <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
      <button type="submit" class="btn-primary" :disabled="saving">
        <LoadingSpinner v-if="saving" size="sm" />
        Speichern
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const ui = useUiStore()
const loading = ref(true)
const saving = ref(false)
const saveError = ref('')
const form = ref({})

const timezones = [
  'Europe/Berlin', 'Europe/Vienna', 'Europe/Zurich', 'Europe/London',
  'Europe/Paris', 'Europe/Amsterdam', 'Europe/Brussels', 'Europe/Rome',
  'Europe/Warsaw', 'Europe/Prague', 'Europe/Budapest', 'Europe/Lisbon',
  'Europe/Stockholm', 'Europe/Helsinki', 'UTC',
]

const impressumVorlage = `<h2>Angaben gemäß § 5 TMG</h2>
<p>
  {{organisation}}<br>
  {{adresse}}<br>
  {{plz_ort}}
</p>
<h3>Vertreten durch</h3>
<p>{{person}}</p>
<h3>Kontakt</h3>
<p>
  Telefon: {{telefon}}<br>
  E-Mail: {{email}}
</p>
<h3>Registereintrag</h3>
<p>
  Eingetragen im Vereinsregister.<br>
  Registergericht: [Amtsgericht Stadt]<br>
  Registernummer: VR [XXXXX]
</p>
<h3>Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV</h3>
<p>{{person}}, {{adresse}}, {{plz_ort}}</p>`

const datenschutzVorlage = `<h2>Datenschutzerklärung</h2>
<h3>1. Verantwortlicher</h3>
<p>
  Verantwortlicher im Sinne der DSGVO ist:<br>
  {{organisation}}<br>
  {{adresse}}, {{plz_ort}}<br>
  E-Mail: {{email}}
</p>
<h3>2. Erhobene Daten und Zweck</h3>
<p>Zur Nutzung dieser Plattform erheben wir folgende personenbezogene Daten:</p>
<ul>
  <li><strong>Name</strong> – zur Identifikation bei Veranstaltungen</li>
  <li><strong>E-Mail-Adresse</strong> (optional) – für Anmeldebestätigungen und Passwort-Reset</li>
  <li><strong>Schicht- und Spendenanmeldungen</strong> – zur Koordination des Standdienstes</li>
</ul>
<p>Rechtsgrundlage: Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung / vorvertragliche Maßnahmen).</p>
<h3>3. Speicherdauer</h3>
<p>
  Personenbezogene Daten werden gelöscht, sobald sie für den Verarbeitungszweck nicht mehr
  benötigt werden, spätestens jedoch [X Monate] nach Ende der Veranstaltung.
  Auf Anfrage erfolgt eine sofortige Löschung (Art. 17 DSGVO).
</p>
<h3>4. Weitergabe an Dritte</h3>
<p>Daten werden nicht an Dritte weitergegeben, außer dies ist gesetzlich vorgeschrieben.</p>
<h3>5. Ihre Rechte</h3>
<p>
  Sie haben das Recht auf Auskunft (Art. 15), Berichtigung (Art. 16), Löschung (Art. 17),
  Einschränkung (Art. 18), Datenübertragbarkeit (Art. 20) und Widerspruch (Art. 21 DSGVO).
  Zur Ausübung Ihrer Rechte wenden Sie sich an: {{email}}
</p>
<h3>6. Cookies und lokale Speicherung</h3>
<p>
  Diese Anwendung verwendet ausschließlich technisch notwendige Cookies (Sitzungs-Token).
  Es werden keine Tracking- oder Werbe-Cookies eingesetzt.
</p>
<h3>7. Beschwerderecht</h3>
<p>
  Sie haben das Recht, sich bei der zuständigen Datenschutz-Aufsichtsbehörde zu beschweren.
</p>`

const legacyImpressumTemplate = `<h2>Angaben gemäß § 5 TMG</h2>
<p>
  [Name des Betreibers / Verein]<br>
  [Straße, Hausnummer]<br>
  [PLZ Ort]
</p>
<h3>Vertreten durch</h3>
<p>[Vorname Nachname, Funktion]</p>
<h3>Kontakt</h3>
<p>
  Telefon: [+49 ...]<br>
  E-Mail: [impressum@beispiel.de]
</p>
<h3>Registereintrag</h3>
<p>
  Eingetragen im Vereinsregister.<br>
  Registergericht: [Amtsgericht Stadt]<br>
  Registernummer: VR [XXXXX]
</p>
<h3>Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV</h3>
<p>[Vorname Nachname, Anschrift]</p>`

onMounted(async () => {
  try {
    const res = await adminApi.getGlobalSettings()
    form.value = res.data.data
  } finally {
    loading.value = false
  }
})

function normalizeWhitelist() {
  if (!form.value.ip_whitelist) return
  form.value.ip_whitelist = form.value.ip_whitelist
    .split(/[\n,]+/)
    .map(s => s.trim())
    .filter(Boolean)
    .join(', ')
}

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    const res = await adminApi.updateGlobalSettings(form.value)
    form.value.updated_at = res.data.data.updated_at
    ui.success('Gespeichert')
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  } finally {
    saving.value = false
  }
}
</script>
