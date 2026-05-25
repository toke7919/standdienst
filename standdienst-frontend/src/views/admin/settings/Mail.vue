<template>
  <div>
    <h1 class="text-2xl font-bold text-ink mb-6">Mail-Einstellungen</h1>
    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <form v-else @submit.prevent="save" class="space-y-4 max-w-2xl card">
      <div><label class="label">SMTP-Server</label><input v-model="form.mail_server" class="input" /></div>
      <div><label class="label">Port</label><input v-model.number="form.mail_port" type="number" class="input max-w-xs" /></div>
      <div class="flex items-center gap-2">
        <input v-model="form.mail_use_tls" type="checkbox" id="tls" />
        <label for="tls" class="text-sm text-ink/80">TLS verwenden</label>
      </div>
      <div><label class="label">Benutzername</label><input v-model="form.mail_username" class="input" /></div>
      <div><label class="label">Passwort</label><input v-model="form.mail_password" type="password" class="input" /></div>
      <div><label class="label">Absender-E-Mail</label><input v-model="form.mail_default_sender" type="email" class="input" /></div>
      <div><label class="label">Absender-Name</label><input v-model="form.mail_sender_name" class="input" /></div>
      <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
      <div class="flex gap-3 flex-wrap items-end">
        <button type="submit" class="btn-primary" :disabled="saving">
          <LoadingSpinner v-if="saving" size="sm" />
          Speichern
        </button>
        <div class="flex items-end gap-2">
          <div>
            <label class="label">Testmail an</label>
            <input v-model="testRecipient" type="email" class="input text-sm" placeholder="empfaenger@beispiel.de" />
          </div>
          <button type="button" class="btn-secondary" :disabled="testing" @click="sendTest">
            <LoadingSpinner v-if="testing" size="sm" />
            Senden
          </button>
        </div>
      </div>
      <p v-if="testResult" class="text-sm" :class="testResult.ok ? 'text-green-700' : 'text-red-600'">
        {{ testResult.message }}
      </p>
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
const testing = ref(false)
const saveError = ref('')
const testResult = ref(null)
const testRecipient = ref('')
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
    const res = await adminApi.updateMailSettings(form.value)
    form.value.updated_at = res.data.data.updated_at
    ui.success('Gespeichert')
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  } finally {
    saving.value = false
  }
}

async function sendTest() {
  testing.value = true
  testResult.value = null
  try {
    const res = await adminApi.sendTestMail({ to: testRecipient.value || undefined })
    testResult.value = { ok: true, message: res.data.message }
  } catch (e) {
    testResult.value = { ok: false, message: e.response?.data?.error || 'Versand fehlgeschlagen' }
  } finally {
    testing.value = false
  }
}
</script>
