<template>
  <div class="max-w-lg">
    <h1 class="text-xl font-bold text-gray-900 mb-6">Mein Profil</h1>

    <div class="card space-y-4 mb-6">
      <h2 class="text-base font-semibold text-gray-800">Daten ändern</h2>
      <form @submit.prevent="save" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label">Vorname</label><input v-model="form.first_name" class="input" required autocomplete="given-name" /></div>
          <div><label class="label">Nachname</label><input v-model="form.last_name" class="input" autocomplete="family-name" /></div>
        </div>
        <div><label class="label">E-Mail</label><input v-model="form.email" type="email" class="input" autocomplete="email" /></div>
        <div>
          <label class="label">Neues Passwort <span class="text-gray-400 font-normal text-xs">(leer lassen zum Beibehalten)</span></label>
          <div class="relative">
            <input
              v-model="form.password"
              :type="showPw ? 'text' : 'password'"
              class="input pr-10"
              autocomplete="new-password"
            />
            <button
              type="button"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              @click="showPw = !showPw"
            >
              <EyeSlashIcon v-if="showPw" class="w-4 h-4" />
              <EyeIcon v-else class="w-4 h-4" />
            </button>
          </div>
        </div>
        <div v-if="form.password">
          <label class="label">Passwort bestätigen</label>
          <input v-model="form.passwordConfirm" type="password" class="input" autocomplete="new-password" />
          <p v-if="form.passwordConfirm && form.password !== form.passwordConfirm" class="text-xs text-red-500 mt-1">
            Passwörter stimmen nicht überein
          </p>
        </div>
        <button type="submit" class="btn-primary" :disabled="saving">
          <LoadingSpinner v-if="saving" size="sm" class="mr-2" />
          Speichern
        </button>
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

    <!-- Abmelden (nur mobil sichtbar) -->
    <div class="card mb-6 md:hidden">
      <h2 class="text-base font-semibold text-gray-800 mb-3">Sitzung</h2>
      <button class="btn-secondary w-full" @click="auth.logout">Abmelden</button>
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
import { EyeIcon, EyeSlashIcon } from '@heroicons/vue/24/outline'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const form = ref({
  first_name: auth.user?.first_name || auth.user?.name || '',
  last_name: auth.user?.last_name || '',
  email: auth.user?.email || '',
  password: '',
  passwordConfirm: '',
})
const saving = ref(false)
const showPw = ref(false)

async function save() {
  if (form.value.password && form.value.password !== form.value.passwordConfirm) {
    ui.err('Passwörter stimmen nicht überein')
    return
  }
  saving.value = true
  const data = { first_name: form.value.first_name, last_name: form.value.last_name, email: form.value.email }
  if (form.value.password) data.password = form.value.password
  try {
    await volunteerApi.updateProfile(route.params.slug, data)
    ui.success('Gespeichert')
    form.value.password = ''
    form.value.passwordConfirm = ''
    await auth.fetchMe()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler beim Speichern')
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
