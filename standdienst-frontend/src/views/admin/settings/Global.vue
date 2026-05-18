<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Globale Einstellungen</h1>

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
          <p class="text-xs text-gray-400 mt-1">
            Soft-gelöschte Volunteers werden nach dieser Frist automatisch permanent gelöscht.
          </p>
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-base font-semibold text-gray-800">Betreiber-Impressum (HTML)</h2>
          <button type="button" class="btn-secondary text-xs py-1 px-2"
                  @click="form.provider_impressum_html = impressumTemplate">
            Vorlage einfügen
          </button>
        </div>
        <textarea v-model="form.provider_impressum_html" class="input font-mono text-xs" rows="10"
                  placeholder="HTML für das Betreiber-Impressum (§ 5 TMG)" />
      </div>

      <div class="card">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-base font-semibold text-gray-800">Landing-Page Impressum (HTML)</h2>
          <button type="button" class="btn-secondary text-xs py-1 px-2"
                  @click="form.landing_impressum_html = impressumTemplate">
            Vorlage einfügen
          </button>
        </div>
        <textarea v-model="form.landing_impressum_html" class="input font-mono text-xs" rows="6"
                  placeholder="HTML für das Impressum auf der Landing-Page" />
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

const impressumTemplate = `<h2>Angaben gemäß § 5 TMG</h2>
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

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    await adminApi.updateGlobalSettings(form.value)
    ui.success('Gespeichert')
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  } finally {
    saving.value = false
  }
}
</script>
