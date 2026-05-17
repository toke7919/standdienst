<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Mail-Einstellungen</h1>
    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <form v-else @submit.prevent="save" class="space-y-4 max-w-2xl card">
      <div><label class="label">SMTP-Server</label><input v-model="form.mail_server" class="input" /></div>
      <div><label class="label">Port</label><input v-model.number="form.mail_port" type="number" class="input max-w-xs" /></div>
      <div class="flex items-center gap-2">
        <input v-model="form.mail_use_tls" type="checkbox" id="tls" />
        <label for="tls" class="text-sm text-gray-700">TLS verwenden</label>
      </div>
      <div><label class="label">Benutzername</label><input v-model="form.mail_username" class="input" /></div>
      <div><label class="label">Passwort</label><input v-model="form.mail_password" type="password" class="input" /></div>
      <div><label class="label">Absender-E-Mail</label><input v-model="form.mail_default_sender" type="email" class="input" /></div>
      <div><label class="label">Absender-Name</label><input v-model="form.mail_sender_name" class="input" /></div>
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
    const res = await adminApi.getMailSettings()
    form.value = res.data.data
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    await adminApi.updateMailSettings(form.value)
    ui.success('Gespeichert')
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  } finally {
    saving.value = false
  }
}
</script>
