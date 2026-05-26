<template>
  <div class="max-w-lg">
    <h1 class="text-xl font-bold text-ink mb-6">Mein Profil</h1>

    <div class="card space-y-4 mb-6">
      <h2 class="text-base font-semibold text-ink">Daten ändern</h2>
      <form @submit.prevent="save" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label">Vorname</label><input v-model="form.first_name" class="input" required autocomplete="given-name" /></div>
          <div><label class="label">Nachname</label><input v-model="form.last_name" class="input" autocomplete="family-name" /></div>
        </div>
        <div><label class="label">E-Mail</label><input v-model="form.email" type="email" class="input" autocomplete="email" /></div>
        <div>
          <label class="label">Neues Passwort <span class="text-muted font-normal text-xs">(leer lassen zum Beibehalten)</span></label>
          <div class="relative">
            <input
              v-model="form.password"
              :type="showPw ? 'text' : 'password'"
              class="input pr-10"
              autocomplete="new-password"
            />
            <button
              type="button"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink/80"
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

    <!-- E-Mail-Benachrichtigungen -->
    <div v-if="mailEnabled && form.email" class="card mb-6">
      <h2 class="text-base font-semibold text-ink mb-3">Benachrichtigungen</h2>
      <div class="space-y-3">
        <label class="flex items-start gap-3 cursor-pointer">
          <div class="relative flex-shrink-0 mt-0.5">
            <input type="checkbox" class="sr-only peer" v-model="form.email_confirmation_enabled" @change="saveEmailConfirmation" />
            <div class="w-10 h-6 bg-sand rounded-full peer-checked:bg-primary-600 transition-colors"></div>
            <div class="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4"></div>
          </div>
          <div>
            <span class="text-sm text-ink/80">Anmeldebestätigung per E-Mail</span>
            <p class="text-xs text-muted mt-0.5">Nach jeder Dienst-Anmeldung eine Bestätigungsmail erhalten</p>
          </div>
        </label>
        <label class="flex items-start gap-3 cursor-pointer">
          <div class="relative flex-shrink-0 mt-0.5">
            <input type="checkbox" class="sr-only peer" v-model="form.notifications_enabled" @change="saveNotifications" />
            <div class="w-10 h-6 bg-sand rounded-full peer-checked:bg-primary-600 transition-colors"></div>
            <div class="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4"></div>
          </div>
          <div>
            <span class="text-sm text-ink/80">Erinnerungsmails aktivieren</span>
            <p class="text-xs text-muted mt-0.5">Einen Tag vor dem Dienst oder der Essensspenden-Abgabe erinnert werden</p>
          </div>
        </label>
      </div>
    </div>

    <!-- DSGVO: Datenauskunft -->
    <div class="card mb-6">
      <h2 class="text-base font-semibold text-ink mb-2">Meine Daten (DSGVO Art. 20)</h2>
      <p class="text-sm text-muted mb-4">
        Lade eine maschinenlesbare Kopie aller über dich gespeicherten Daten herunter.
      </p>
      <button class="btn-secondary" :disabled="exportLoading" @click="exportData">
        <LoadingSpinner v-if="exportLoading" size="sm" class="mr-2" />
        Daten exportieren (JSON)
      </button>
    </div>

    <!-- Abmelden (nur mobil sichtbar) -->
    <div class="card mb-6 md:hidden">
      <h2 class="text-base font-semibold text-ink mb-3">Sitzung</h2>
      <button class="btn-secondary w-full" @click="auth.volunteerLogout(route.params.slug)">Abmelden</button>
    </div>

    <div class="mt-8 pt-6 border-t-2 border-dashed border-red-100">
      <div class="flex items-center gap-2 mb-4">
        <ExclamationTriangleIcon class="w-4 h-4 text-red-400" />
        <p class="text-xs font-bold uppercase tracking-widest text-red-400">Gefahrenzone</p>
      </div>
      <div class="card border-red-200">
        <h2 class="text-base font-semibold text-red-700 mb-2">Konto löschen</h2>
        <p class="text-sm text-muted mb-4">
          Deine Daten werden pseudonymisiert und sind danach nicht mehr zugänglich (DSGVO-konformes Soft-Delete).
        </p>
        <button class="btn-danger" @click="deleteAccount">Konto löschen</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useInstanceStore } from '@/stores/instance'
import { useUiStore } from '@/stores/ui'
import { volunteerApi } from '@/api/volunteer'
import { EyeIcon, EyeSlashIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const instanceStore = useInstanceStore()
const ui = useUiStore()

const mailEnabled = computed(() => instanceStore.current?.mail_enabled ?? false)

const form = ref({
  first_name: auth.user?.first_name || auth.user?.name || '',
  last_name: auth.user?.last_name || '',
  email: auth.user?.email || '',
  password: '',
  passwordConfirm: '',
  notifications_enabled: auth.user?.notifications_enabled ?? false,
  email_confirmation_enabled: auth.user?.email_confirmation_enabled ?? true,
})
const saving = ref(false)
const showPw = ref(false)

async function save() {
  if (form.value.password && form.value.password !== form.value.passwordConfirm) {
    ui.err('Passwörter stimmen nicht überein')
    return
  }
  saving.value = true
  const data = {
    first_name: form.value.first_name,
    last_name: form.value.last_name,
    email: form.value.email,
    notifications_enabled: form.value.notifications_enabled,
    email_confirmation_enabled: form.value.email_confirmation_enabled,
  }
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

async function saveEmailConfirmation() {
  try {
    await volunteerApi.updateProfile(route.params.slug, {
      email_confirmation_enabled: form.value.email_confirmation_enabled,
    })
    await auth.fetchMe()
    ui.success(form.value.email_confirmation_enabled ? 'Bestätigungsmail aktiviert' : 'Bestätigungsmail deaktiviert')
  } catch {
    form.value.email_confirmation_enabled = !form.value.email_confirmation_enabled
    ui.err('Fehler beim Speichern')
  }
}

async function saveNotifications() {
  try {
    await volunteerApi.updateProfile(route.params.slug, {
      notifications_enabled: form.value.notifications_enabled,
    })
    await auth.fetchMe()
    ui.success(form.value.notifications_enabled ? 'Erinnerungen aktiviert' : 'Erinnerungen deaktiviert')
  } catch {
    form.value.notifications_enabled = !form.value.notifications_enabled
    ui.err('Fehler beim Speichern')
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
    await auth.volunteerLogout(route.params.slug)
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
