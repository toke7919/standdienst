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
        <div class="flex items-center gap-2">
          <input v-model="form.site_locked" type="checkbox" id="locked" />
          <label for="locked" class="text-sm text-gray-700">Anmeldung gesperrt</label>
        </div>
        <div v-if="form.site_locked">
          <label class="label">Sperr-Nachricht</label>
          <textarea v-model="form.lock_message" class="input" rows="3" />
        </div>
        <div>
          <label class="label">Anmeldeschluss</label>
          <input v-model="form.registration_deadline" type="datetime-local" class="input max-w-xs" />
        </div>
      </div>

      <div class="card">
        <h2 class="text-base font-semibold text-gray-800 mb-3">Impressum der Instanz (HTML)</h2>
        <textarea v-model="form.instance_impressum_html" class="input" rows="6" />
      </div>

      <div class="card">
        <h2 class="text-base font-semibold text-gray-800 mb-3">Datenschutzerklärung (HTML)</h2>
        <textarea v-model="form.privacy_policy_html" class="input" rows="6" />
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
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const loading = ref(true)
const saving = ref(false)
const saveError = ref('')
const form = ref({})

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
    await adminApi.updateSiteSettings(route.params.slug, form.value)
    ui.success('Einstellungen gespeichert')
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  } finally {
    saving.value = false
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
