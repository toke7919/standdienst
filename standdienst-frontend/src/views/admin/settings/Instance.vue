<template>
  <div>
    <h1 class="text-2xl font-bold text-ink mb-6">Instanz-Einstellungen</h1>

    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <form v-else @submit.prevent="save" class="space-y-6 max-w-2xl">
      <div class="card space-y-4">
        <h2 class="text-base font-semibold text-ink">Allgemein</h2>
        <div><label class="label">Seitentitel</label><input v-model="form.site_title" class="input" required /></div>
        <div>
          <label class="label">Primärfarbe</label>
          <div class="flex items-center gap-3">
            <input
              type="color"
              :value="form.primary_color || '#a51f2c'"
              class="h-10 w-20 rounded cursor-pointer border border-sand"
              @input="form.primary_color = $event.target.value"
            />
            <input v-model="form.primary_color" class="input max-w-32" placeholder="Anwendungsstandard" />
            <button v-if="form.primary_color" type="button" class="btn-secondary text-xs py-1.5" @click="form.primary_color = null">Zurücksetzen</button>
          </div>
          <p class="text-xs text-muted mt-1">Leer lassen = Anwendungsstandard-Farbschema verwenden</p>
        </div>
        <div>
          <label class="label">Logo</label>
          <div class="flex items-center gap-3 flex-wrap">
            <input type="file" accept="image/*" class="text-sm" @change="uploadLogo" />
            <button v-if="form.logo_filename" type="button" class="btn-secondary text-xs py-1.5" @click="removeLogo">Entfernen</button>
          </div>
          <img v-if="form.logo_filename" :src="`/uploads/${form.logo_filename}`" class="mt-2 h-16 object-contain" alt="Logo" />
          <p v-else class="text-xs text-muted mt-1">Kein Logo – Anwendungsstandard wird verwendet</p>
        </div>
      </div>

      <div class="card space-y-4">
        <h2 class="text-base font-semibold text-ink">Funktionen</h2>
        <div class="flex items-center gap-2">
          <input v-model="form.shifts_enabled" type="checkbox" id="shifts" />
          <label for="shifts" class="text-sm text-ink/80">Dienste aktiviert</label>
        </div>
        <div class="flex items-center gap-2">
          <input v-model="form.food_donations_enabled" type="checkbox" id="food" />
          <label for="food" class="text-sm text-ink/80">Essensspenden aktiviert</label>
        </div>
<div class="flex items-center gap-2">
          <input v-model="form.site_locked" type="checkbox" id="locked" />
          <label for="locked" class="text-sm text-ink/80">Anmeldung gesperrt</label>
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
        <div>
          <label class="label">Abmeldeschluss (Stunden vor Dienstbeginn)</label>
          <input
            v-model.number="form.unregister_deadline_hours"
            type="number"
            min="1"
            max="168"
            class="input max-w-xs"
            placeholder="Leer lassen = keine Einschränkung"
          />
          <p class="text-xs text-muted mt-1">
            Helfer können sich bis zu dieser Zeit vor Dienstbeginn abmelden. Leer lassen für keine Einschränkung.
          </p>
        </div>
      </div>

      <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
      <div class="flex items-center gap-3">
        <button type="submit" class="btn-primary" :disabled="saving || resetting">
          <LoadingSpinner v-if="saving" size="sm" />
          Speichern
        </button>
        <button type="button" class="btn-secondary text-sm" :disabled="saving || resetting" @click="resetSettings">
          <LoadingSpinner v-if="resetting" size="sm" />
          Einstellungen zurücksetzen
        </button>
      </div>
    </form>

    <!-- Gefahrenzone: nur für globale Admins -->
    <div v-if="auth.isAdmin" class="max-w-2xl mt-10">
      <div class="card border-red-200 bg-red-50 space-y-3">
        <h2 class="text-base font-semibold text-red-800">Gefahrenzone</h2>
        <p class="text-sm text-red-700">
          Löscht alle Helfer, Stände, Termine, Dienste, Anmeldungen und Essensspenden dieser Instanz.
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
const resetting = ref(false)
const saveError = ref('')
const form = ref({})

const lockTemplate = 'Die Anmeldung ist derzeit geschlossen. Bitte versuche es später erneut oder wende dich an den Veranstalter.'

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
    instanceStore.invalidateCache()
    if (form.value.primary_color) applyTheme(form.value.primary_color)
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
    message: 'Alle Helfer, Stände, Termine, Dienste und Anmeldungen dieser Instanz werden unwiderruflich gelöscht. Fortfahren?',
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

async function resetSettings() {
  const ok = await ui.confirm({
    title: 'Einstellungen zurücksetzen',
    message: 'Seitentitel wird auf "Standdienst" gesetzt, Primärfarbe und Logo werden entfernt. Das Anwendungsstandard-Design wird verwendet. Fortfahren?',
    confirmText: 'Zurücksetzen',
    danger: false,
  })
  if (!ok) return
  resetting.value = true
  try {
    if (form.value.logo_filename) await adminApi.deleteLogo(route.params.slug)
    form.value.site_title = 'Standdienst'
    form.value.primary_color = null
    form.value.logo_filename = null
    const res = await adminApi.updateSiteSettings(route.params.slug, form.value)
    form.value.updated_at = res.data.data.updated_at
    instanceStore.invalidateCache()
    ui.success('Einstellungen zurückgesetzt')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler beim Zurücksetzen')
  } finally {
    resetting.value = false
  }
}

async function removeLogo() {
  try {
    await adminApi.deleteLogo(route.params.slug)
    form.value.logo_filename = null
    ui.success('Logo entfernt')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler beim Entfernen')
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
    if (res.data.data.updated_at) form.value.updated_at = res.data.data.updated_at
    ui.success('Logo hochgeladen')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Upload fehlgeschlagen')
  }
}
</script>
