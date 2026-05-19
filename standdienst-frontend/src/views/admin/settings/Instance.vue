<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Instanz-Einstellungen</h1>

    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <form v-else @submit.prevent="save" class="space-y-6 max-w-2xl">
      <div class="card space-y-4">
        <h2 class="text-base font-semibold text-gray-800">Allgemein</h2>
        <div><label class="label">Seitentitel</label><input v-model="form.site_title" class="input" required /></div>
        <div>
          <label class="label">Primärfarbe</label>
          <div class="flex items-center gap-3">
            <input v-model="form.primary_color" type="color" class="h-10 w-20 rounded cursor-pointer border border-gray-300" />
            <input v-model="form.primary_color" class="input max-w-32" placeholder="#4f46e5" />
          </div>
        </div>
        <div>
          <label class="label">Logo</label>
          <input type="file" accept="image/*" class="text-sm" @change="uploadLogo" />
          <img v-if="form.logo_filename" :src="`/uploads/${form.logo_filename}`" class="mt-2 h-16 object-contain" alt="Logo" />
        </div>
      </div>

      <div class="card space-y-4">
        <h2 class="text-base font-semibold text-gray-800">Funktionen</h2>
        <div class="flex items-center gap-2">
          <input v-model="form.shifts_enabled" type="checkbox" id="shifts" />
          <label for="shifts" class="text-sm text-gray-700">Schichten aktiviert</label>
        </div>
        <div class="flex items-center gap-2">
          <input v-model="form.food_donations_enabled" type="checkbox" id="food" />
          <label for="food" class="text-sm text-gray-700">Essensspenden aktiviert</label>
        </div>
        <div class="flex items-center gap-2 ml-5">
          <input v-model="form.food_refrigeration_enabled" type="checkbox" id="food-refrig"
                 :disabled="!form.food_donations_enabled" />
          <label for="food-refrig" class="text-sm text-gray-700"
                 :class="{ 'opacity-50': !form.food_donations_enabled }">
            Kühlung-Option bei Essensspenden anzeigen
          </label>
        </div>
        <div class="flex items-center gap-2">
          <input v-model="form.site_locked" type="checkbox" id="locked" />
          <label for="locked" class="text-sm text-gray-700">Anmeldung gesperrt</label>
        </div>
        <div v-if="form.site_locked">
          <div class="flex items-center justify-between mb-1">
            <label class="label">Sperr-Nachricht</label>
            <button type="button" class="btn-secondary text-xs py-1 px-2"
                    @click="form.lock_message = lockTemplate">
              Vorlage einfügen
            </button>
          </div>
          <textarea v-model="form.lock_message" class="input" rows="3" />
        </div>
        <div>
          <label class="label">Anmeldeschluss</label>
          <input v-model="form.registration_deadline" type="datetime-local" class="input max-w-xs" />
        </div>
      </div>

      <div class="card">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-base font-semibold text-gray-800">Impressum der Instanz (HTML)</h2>
          <button type="button" class="btn-secondary text-xs py-1 px-2"
                  @click="form.instance_impressum_html = impressumTemplate">
            Vorlage einfügen
          </button>
        </div>
        <textarea v-model="form.instance_impressum_html" class="input font-mono text-xs" rows="8" />
      </div>

      <div class="card">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-base font-semibold text-gray-800">Datenschutzerklärung (HTML)</h2>
          <button type="button" class="btn-secondary text-xs py-1 px-2"
                  @click="form.privacy_policy_html = datenschutzTemplate">
            Vorlage einfügen
          </button>
        </div>
        <textarea v-model="form.privacy_policy_html" class="input font-mono text-xs" rows="8" />
      </div>

      <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
      <button type="submit" class="btn-primary" :disabled="saving">
        <LoadingSpinner v-if="saving" size="sm" />
        Speichern
      </button>
    </form>

    <!-- Gefahrenzone: nur für globale Admins -->
    <div v-if="auth.isAdmin" class="max-w-2xl mt-10">
      <div class="card border-red-200 bg-red-50 space-y-3">
        <h2 class="text-base font-semibold text-red-800">Gefahrenzone</h2>
        <p class="text-sm text-red-700">
          Löscht alle Helfer, Stände, Termine, Schichten, Anmeldungen und Essensspenden dieser Instanz.
          Die Instanz selbst und ihre Einstellungen bleiben erhalten. Diese Aktion ist
          <strong>nicht umkehrbar</strong>.
        </p>
        <button class="btn-primary bg-red-600 hover:bg-red-700 text-sm" :disabled="clearing" @click="clearData">
          <LoadingSpinner v-if="clearing" size="sm" />
          Alle Instanzdaten löschen
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { useInstanceStore } from '@/stores/instance'
import { applyTheme } from '@/utils/colorPalette'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const auth = useAuthStore()
const instanceStore = useInstanceStore()
const loading = ref(true)
const saving = ref(false)
const clearing = ref(false)
const saveError = ref('')
const form = ref({})

const lockTemplate = 'Die Anmeldung ist derzeit geschlossen. Bitte versuche es später erneut oder wende dich an den Veranstalter.'

const impressumTemplate = `<h2>Angaben gemäß § 5 TMG</h2>
<p>
  [Name des Veranstalters / Vereins]<br>
  [Straße, Hausnummer]<br>
  [PLZ Ort]
</p>
<h3>Vertreten durch</h3>
<p>[Vorname Nachname, Funktion]</p>
<h3>Kontakt</h3>
<p>
  Telefon: [+49 ...]<br>
  E-Mail: [kontakt@beispiel.de]
</p>`

const datenschutzTemplate = `<h2>Datenschutzerklärung</h2>
<h3>1. Verantwortlicher</h3>
<p>
  Verantwortlicher im Sinne der DSGVO ist:<br>
  [Name / Organisation]<br>
  [Adresse]<br>
  E-Mail: [kontakt@beispiel.de]
</p>
<h3>2. Erhobene Daten und Zweck</h3>
<p>Zur Nutzung dieser Plattform erheben wir folgende personenbezogene Daten:</p>
<ul>
  <li><strong>Name</strong> – zur Identifikation bei der Veranstaltung</li>
  <li><strong>E-Mail-Adresse</strong> (optional) – für Anmeldebestätigungen und Passwort-Reset</li>
  <li><strong>Schicht- und Spendenanmeldungen</strong> – zur Koordination des Standdienstes</li>
</ul>
<p>Rechtsgrundlage: Art. 6 Abs. 1 lit. b DSGVO.</p>
<h3>3. Speicherdauer</h3>
<p>Personenbezogene Daten werden nach Ende der Veranstaltung gelöscht. Auf Anfrage erfolgt eine sofortige Löschung (Art. 17 DSGVO).</p>
<h3>4. Ihre Rechte</h3>
<p>Auskunft (Art. 15), Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung (Art. 18), Datenübertragbarkeit (Art. 20). Kontakt: [kontakt@beispiel.de]</p>`

onMounted(async () => {
  try {
    const res = await adminApi.getSiteSettings(route.params.slug)
    form.value = res.data.data
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    const res = await adminApi.updateSiteSettings(route.params.slug, form.value)
    form.value.updated_at = res.data.data.updated_at
    if (form.value.primary_color) {
      applyTheme(form.value.primary_color)
      instanceStore.invalidateCache()
    }
    ui.success('Einstellungen gespeichert')
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  } finally {
    saving.value = false
  }
}

async function clearData() {
  const ok = await ui.confirm({
    title: 'Alle Instanzdaten löschen',
    message: 'Alle Helfer, Stände, Termine, Schichten und Anmeldungen dieser Instanz werden unwiderruflich gelöscht. Fortfahren?',
    confirmText: 'Endgültig löschen',
    danger: true,
  })
  if (!ok) return
  clearing.value = true
  try {
    await adminApi.clearInstanceData(route.params.slug)
    ui.success('Instanzdaten gelöscht')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler beim Löschen')
  } finally {
    clearing.value = false
  }
}

async function uploadLogo(event) {
  const file = event.target.files[0]
  if (!file) return
  const fd = new FormData()
  fd.append('logo', file)
  try {
    const res = await adminApi.uploadLogo(route.params.slug, fd)
    form.value.logo_filename = res.data.data.logo_filename
    ui.success('Logo hochgeladen')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Upload fehlgeschlagen')
  }
}
</script>
