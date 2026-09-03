<template>
  <div class="min-h-screen bg-gradient-to-br from-bg-brand to-soft flex items-center justify-center p-4">
    <div class="w-full max-w-lg">

      <!-- Header -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-md bg-primary-600 text-white text-2xl font-bold mb-4">
          S
        </div>
        <h1 class="text-2xl font-bold text-ink">Standdienst einrichten</h1>
        <p class="text-muted mt-1 text-sm">Ersteinrichtung – Schritt {{ step }} von {{ totalSteps }}</p>
      </div>

      <!-- Fortschrittsleiste -->
      <div class="flex gap-1.5 mb-8">
        <div v-for="i in totalSteps" :key="i"
             class="h-1.5 flex-1 rounded-full transition-colors duration-300"
             :class="i <= step ? 'bg-primary-600' : 'bg-sand'" />
      </div>

      <!-- ── Schritt 1: Willkommen ── -->
      <div v-if="step === 1" class="card">
        <h2 class="text-lg font-semibold text-ink mb-3">Willkommen</h2>
        <p class="text-ink/80 text-sm mb-4">
          Standdienst wurde erfolgreich installiert. Dieser Assistent führt dich in wenigen
          Schritten durch die Ersteinrichtung.
        </p>
        <ul class="space-y-2 mb-6 text-sm text-ink/80">
          <li class="flex items-center gap-2"><span class="text-primary-600 font-semibold">1.</span> Admin-Account anlegen</li>
          <li class="flex items-center gap-2"><span class="text-primary-600 font-semibold">2.</span> Basis-URL konfigurieren</li>
          <li class="flex items-center gap-2"><span class="text-primary-600 font-semibold">3.</span> Mail-Server einrichten (optional)</li>
        </ul>
        <button class="btn-primary w-full" @click="step = 2">Einrichtung starten</button>
      </div>

      <!-- ── Schritt 2: Admin-Account ── -->
      <div v-else-if="step === 2" class="card">
        <h2 class="text-lg font-semibold text-ink mb-1">Admin-Account</h2>
        <p class="text-sm text-muted mb-5">
          Dieser Account hat vollen Zugriff auf die gesamte Plattform.
        </p>
        <form @submit.prevent="submitAdmin" class="space-y-4">
          <div>
            <label class="label">E-Mail-Adresse</label>
            <input v-model="admin.email" type="email" class="input" required
                   autocomplete="email" placeholder="admin@example.com" />
          </div>
          <div>
            <label class="label">Passwort</label>
            <input v-model="admin.password" type="password" class="input" required
                   autocomplete="new-password" placeholder="Mindestens 8 Zeichen" />
            <p class="text-xs text-muted mt-1">Mind. 8 Zeichen, 1 Ziffer, 1 Sonderzeichen</p>
          </div>
          <div>
            <label class="label">Passwort bestätigen</label>
            <input v-model="admin.passwordConfirm" type="password" class="input" required
                   autocomplete="new-password" />
          </div>
          <p v-if="errors.admin" class="text-sm text-red-600">{{ errors.admin }}</p>
          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="step = 1">Zurück</button>
            <button type="submit" class="btn-primary flex-1" :disabled="loading">
              <LoadingSpinner v-if="loading" size="sm" class="mr-2" />
              Weiter
            </button>
          </div>
        </form>
      </div>

      <!-- ── Schritt 3: Basis-URL ── -->
      <div v-else-if="step === 3" class="card">
        <h2 class="text-lg font-semibold text-ink mb-1">Basis-URL</h2>
        <p class="text-sm text-muted mb-5">
          Die öffentliche Adresse der Anwendung – wird in E-Mails und QR-Codes verwendet.
        </p>
        <form @submit.prevent="submitConfig" class="space-y-4">
          <div>
            <label class="label">Basis-URL</label>
            <input v-model="config.base_url" type="url" class="input"
                   placeholder="https://standdienst.example.com" />
            <p class="text-xs text-muted mt-1">Ohne abschließenden Slash. Leer lassen = später konfigurieren.</p>
          </div>
          <div>
            <label class="label">Copyright-Text <span class="text-muted text-xs">(optional)</span></label>
            <input v-model="config.copyright_text" class="input"
                   placeholder="© 2026 Mein Verein" />
          </div>
          <div>
            <label class="label">Zeitzone</label>
            <select v-model="config.timezone" class="input">
              <option v-for="tz in timezones" :key="tz" :value="tz">{{ tz }}</option>
            </select>
          </div>
          <p v-if="errors.config" class="text-sm text-red-600">{{ errors.config }}</p>
          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="step = 2">Zurück</button>
            <button type="submit" class="btn-primary flex-1" :disabled="loading">
              <LoadingSpinner v-if="loading" size="sm" class="mr-2" />
              Weiter
            </button>
          </div>
        </form>
      </div>

      <!-- ── Schritt 4: Mail-Server ── -->
      <div v-else-if="step === 4" class="card">
        <h2 class="text-lg font-semibold text-ink mb-1">Mail-Server</h2>
        <p class="text-sm text-muted mb-1">
          Für Willkommens-Mails und Passwort-Reset-Links. Kann später in den Admin-Einstellungen
          geändert werden.
        </p>
        <button class="text-xs text-primary-600 underline mb-5" type="button"
                @click="finishSetup">Diesen Schritt überspringen →</button>

        <form @submit.prevent="submitMail" class="space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2 sm:col-span-1">
              <label class="label">SMTP-Server</label>
              <input v-model="mail.server" class="input" placeholder="smtp.example.com" />
            </div>
            <div>
              <label class="label">Port</label>
              <input v-model.number="mail.port" type="number" class="input" placeholder="587" />
            </div>
          </div>
          <div class="flex items-center gap-3">
            <input v-model="mail.use_tls" type="checkbox" id="tls" class="rounded" />
            <label for="tls" class="text-sm text-ink/80">TLS verwenden</label>
          </div>
          <div>
            <label class="label">Benutzername</label>
            <input v-model="mail.username" class="input" autocomplete="username"
                   placeholder="user@example.com" />
          </div>
          <div>
            <label class="label">Passwort</label>
            <input v-model="mail.password" type="password" class="input"
                   autocomplete="current-password" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Absender-Adresse</label>
              <input v-model="mail.sender" class="input" type="email"
                     placeholder="noreply@example.com" />
            </div>
            <div>
              <label class="label">Absender-Name</label>
              <input v-model="mail.sender_name" class="input" placeholder="Standdienst" />
            </div>
          </div>
          <p v-if="errors.mail" class="text-sm text-red-600">{{ errors.mail }}</p>
          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="step = 3">Zurück</button>
            <button type="submit" class="btn-primary flex-1" :disabled="loading">
              <LoadingSpinner v-if="loading" size="sm" class="mr-2" />
              Speichern & abschließen
            </button>
          </div>
        </form>
      </div>

      <!-- ── Schritt 5: Fertig ── -->
      <div v-else-if="step === 5" class="card text-center">
        <div class="text-5xl mb-4">🎉</div>
        <h2 class="text-xl font-bold text-ink mb-2">Einrichtung abgeschlossen!</h2>
        <p class="text-ink/80 text-sm mb-6">
          Standdienst ist betriebsbereit. Melde dich jetzt mit deinem Admin-Account an, um
          die erste Instanz anzulegen.
        </p>
        <div class="space-y-3">
          <RouterLink to="/admin/login" class="btn-primary w-full inline-flex justify-center">
            Zum Admin-Login
          </RouterLink>
          <p class="text-xs text-muted">
            Weitere Einstellungen findest du unter Admin → Einstellungen
          </p>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { setupApi } from '@/api/setup'
import { useSetupStore } from '@/stores/setup'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const setupStore = useSetupStore()
const step = ref(1)
const totalSteps = 4
const loading = ref(false)
const errors = ref({ admin: '', config: '', mail: '' })

const timezones = [
  'Europe/Berlin', 'Europe/Vienna', 'Europe/Zurich', 'Europe/London',
  'Europe/Paris', 'Europe/Amsterdam', 'Europe/Brussels', 'Europe/Rome',
  'Europe/Warsaw', 'Europe/Prague', 'Europe/Budapest', 'Europe/Lisbon',
  'Europe/Stockholm', 'Europe/Helsinki', 'UTC',
]

const admin = ref({ email: '', password: '', passwordConfirm: '' })
const config = ref({ base_url: '', copyright_text: '', timezone: 'Europe/Berlin' })
const mail = ref({
  server: '', port: 587, use_tls: true,
  username: '', password: '', sender: '', sender_name: 'Standdienst',
})

async function submitAdmin() {
  errors.value.admin = ''
  if (admin.value.password !== admin.value.passwordConfirm) {
    errors.value.admin = 'Passwörter stimmen nicht überein'
    return
  }
  loading.value = true
  try {
    await setupApi.createAdmin({ email: admin.value.email, password: admin.value.password })
    step.value = 3
  } catch (e) {
    errors.value.admin = e.response?.data?.error || 'Fehler beim Anlegen des Accounts'
  } finally {
    loading.value = false
  }
}

async function submitConfig() {
  errors.value.config = ''
  loading.value = true
  try {
    await setupApi.saveConfig({
      base_url: config.value.base_url,
      copyright_text: config.value.copyright_text,
      timezone: config.value.timezone,
    })
    step.value = 4
  } catch (e) {
    errors.value.config = e.response?.data?.error || 'Fehler beim Speichern'
  } finally {
    loading.value = false
  }
}

async function submitMail() {
  errors.value.mail = ''
  loading.value = true
  try {
    await setupApi.saveMail(mail.value)
    await finishSetup()
  } catch (e) {
    errors.value.mail = e.response?.data?.error || 'Fehler beim Speichern'
    loading.value = false
  }
}

async function finishSetup() {
  loading.value = true
  try {
    await setupApi.finish()
    setupStore.markComplete()
    step.value = 5
  } catch (e) {
    errors.value.mail = e.response?.data?.error || 'Fehler beim Abschließen'
  } finally {
    loading.value = false
  }
}
</script>
