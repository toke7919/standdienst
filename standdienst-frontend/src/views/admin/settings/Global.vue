<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Globale Einstellungen</h1>

    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <form v-else @submit.prevent="save" class="space-y-6 max-w-2xl">
      <div class="card space-y-4">
        <div><label class="label">Basis-URL</label><input v-model="form.base_url" class="input" placeholder="https://example.com" /></div>
        <div><label class="label">Copyright-Text</label><input v-model="form.copyright_text" class="input" /></div>
        <div><label class="label">Log-Aufbewahrung (Monate)</label><input v-model.number="form.log_retention_months" type="number" min="1" max="60" class="input max-w-xs" /></div>
      </div>

      <div class="card space-y-4">
        <h2 class="text-base font-semibold text-gray-800">SMB-Backup</h2>
        <div class="flex items-center gap-2">
          <input v-model="form.smb_enabled" type="checkbox" id="smb" />
          <label for="smb" class="text-sm text-gray-700">SMB-Backup aktiviert</label>
        </div>
        <template v-if="form.smb_enabled">
          <div><label class="label">Server</label><input v-model="form.smb_server" class="input" placeholder="192.168.1.100" /></div>
          <div><label class="label">Share</label><input v-model="form.smb_share" class="input" placeholder="backup" /></div>
          <div><label class="label">Pfad</label><input v-model="form.smb_path" class="input" placeholder="/standdienst" /></div>
          <div><label class="label">Benutzername</label><input v-model="form.smb_username" class="input" /></div>
          <div><label class="label">Passwort</label><input v-model="form.smb_password" type="password" class="input" /></div>
        </template>
      </div>

      <div class="card">
        <h2 class="text-base font-semibold text-gray-800 mb-3">Betreiber-Impressum (HTML)</h2>
        <textarea v-model="form.provider_impressum_html" class="input" rows="6" />
      </div>

      <div class="card">
        <h2 class="text-base font-semibold text-gray-800 mb-3">Landing-Page Impressum (HTML)</h2>
        <textarea v-model="form.landing_impressum_html" class="input" rows="4" />
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
