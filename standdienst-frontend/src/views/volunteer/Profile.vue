<template>
  <div class="max-w-lg">
    <h1 class="text-xl font-bold text-gray-900 mb-6">Mein Profil</h1>

    <div class="card space-y-4 mb-6">
      <h2 class="text-base font-semibold text-gray-800">Daten ändern</h2>
      <form @submit.prevent="save" class="space-y-4">
        <div><label class="label">Name</label><input v-model="form.name" class="input" required /></div>
        <div><label class="label">E-Mail</label><input v-model="form.email" type="email" class="input" /></div>
        <div>
          <label class="label">Neues Passwort (leer lassen zum Beibehalten)</label>
          <input v-model="form.password" type="password" class="input" autocomplete="new-password" />
        </div>
        <p v-if="saveMsg" class="text-sm" :class="saveOk ? 'text-green-700' : 'text-red-600'">{{ saveMsg }}</p>
        <button type="submit" class="btn-primary" :disabled="saving">Speichern</button>
      </form>
    </div>

    <!-- DSGVO: Datenauskunft -->
    <div class="card mb-6">
      <h2 class="text-base font-semibold text-gray-800 mb-2">Meine Daten (DSGVO Art. 20)</h2>
      <p class="text-sm text-gray-500 mb-4">
        Lade eine maschinenlesbare Kopie aller über dich gespeicherten Daten herunter.
      </p>
      <button class="btn-secondary" :disabled="exportLoading" @click="exportData">
        <LoadingSpinner v-if="exportLoading" size="sm" class="mr-2" />
        Daten exportieren (JSON)
      </button>
    </div>

    <div class="card border-red-200">
      <h2 class="text-base font-semibold text-red-700 mb-2">Konto löschen</h2>
      <p class="text-sm text-gray-500 mb-4">
        Deine Daten werden pseudonymisiert und sind danach nicht mehr zugänglich (DSGVO-konformes Soft-Delete).
      </p>
      <button class="btn-danger" @click="deleteAccount">Konto löschen</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { volunteerApi } from '@/api/volunteer'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const form = ref({
  name: auth.user?.name || '',
  email: auth.user?.email || '',
  password: '',
})
const saving = ref(false)
const saveMsg = ref('')
const saveOk = ref(true)

async function save() {
  saving.value = true
  saveMsg.value = ''
  const data = { name: form.value.name, email: form.value.email }
  if (form.value.password) data.password = form.value.password
  try {
    await volunteerApi.updateProfile(route.params.slug, data)
    saveMsg.value = 'Gespeichert'
    saveOk.value = true
    await auth.fetchMe()
  } catch (e) {
    saveMsg.value = e.response?.data?.error || 'Fehler'
    saveOk.value = false
  } finally {
    saving.value = false
  }
}

const exportLoading = ref(false)

async function exportData() {
  exportLoading.value = true
  try {
    const res = await volunteerApi.getMeineDaten(route.params.slug)
    const blob = new Blob([JSON.stringify(res.data.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `meine-daten-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ui.err(e.response?.data?.error || 'Export fehlgeschlagen')
  } finally {
    exportLoading.value = false
  }
}

async function deleteAccount() {
  const ok = await ui.confirm({
    title: 'Konto löschen',
    message: 'Bist du sicher? Diese Aktion kann nicht rückgängig gemacht werden.',
    confirmText: 'Konto löschen',
    danger: true,
  })
  if (!ok) return
  try {
    await volunteerApi.deleteAccount(route.params.slug)
    await auth.logout()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
