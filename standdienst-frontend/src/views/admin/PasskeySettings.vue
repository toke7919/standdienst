<template>
  <div class="max-w-md">
    <h1 class="text-2xl font-bold text-ink mb-6">Passkeys</h1>

    <div class="card space-y-6">
      <p class="text-sm text-ink/80">
        Passkeys ermöglichen passwortlose Anmeldung mit Fingerabdruck, Gesichtserkennung oder PIN.
        Gespeichert werden sie sicher auf deinem Gerät oder in deinem Passwort-Manager.
      </p>

      <div v-if="!passkeySupported" class="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800">
        Passkeys sind in diesem Kontext nicht verfügbar.
        {{ !window.isSecureContext ? 'Passkeys erfordern HTTPS (außer auf localhost).' : 'Dein Browser unterstützt keine Passkeys.' }}
      </div>

      <!-- Passkey-Liste -->
      <div v-if="credentials.length > 0" class="space-y-2">
        <p class="text-sm font-medium text-ink/80">Registrierte Passkeys</p>
        <div v-for="cred in credentials" :key="cred.id"
             class="flex items-center justify-between rounded-lg border border-sand px-3 py-2">
          <div>
            <p class="text-sm font-medium text-ink">{{ cred.name }}</p>
            <p class="text-xs text-muted">
              Erstellt: {{ formatDate(cred.created_at) }}
              <span v-if="cred.last_used_at"> · Zuletzt verwendet: {{ formatDate(cred.last_used_at) }}</span>
            </p>
          </div>
          <button class="text-red-500 hover:text-red-700 p-1" title="Löschen"
                  @click="remove(cred)">
            <TrashIcon class="w-4 h-4" />
          </button>
        </div>
      </div>
      <p v-else-if="loaded" class="text-sm text-muted">Noch keine Passkeys registriert.</p>

      <!-- Neuen Passkey hinzufügen -->
      <div v-if="passkeySupported && credentials.length < 5">
        <div v-if="!adding">
          <button class="btn-primary" :disabled="loading" @click="adding = true">
            <KeyIcon class="w-4 h-4 mr-1" />
            Passkey hinzufügen
          </button>
        </div>
        <div v-else class="space-y-3">
          <div>
            <label class="label">Name (optional)</label>
            <input v-model="newName" type="text" class="input" placeholder="z.B. MacBook, iPhone"
                   maxlength="100" />
          </div>
          <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
          <div class="flex gap-2">
            <button class="btn-primary" :disabled="registering" @click="register">
              <LoadingSpinner v-if="registering" size="sm" />
              Registrieren
            </button>
            <button class="btn-secondary" @click="adding = false; errorMsg = ''">
              Abbrechen
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { KeyIcon, TrashIcon } from '@heroicons/vue/24/outline'
import { useUiStore } from '@/stores/ui'
import { authApi } from '@/api/auth'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import {
  prepareRegistrationOptions,
  serializeRegistrationCredential,
} from '@/utils/webauthn'

const ui = useUiStore()
const credentials = ref([])
const loaded = ref(false)
const loading = ref(false)
const registering = ref(false)
const adding = ref(false)
const newName = ref('')
const errorMsg = ref('')
const passkeySupported = ref(false)

onMounted(async () => {
  passkeySupported.value = !!(
    window.PublicKeyCredential &&
    navigator.credentials?.create &&
    window.isSecureContext
  )
  await load()
})

async function load() {
  loading.value = true
  try {
    const { data } = await authApi.passkeyList()
    credentials.value = data.credentials
    loaded.value = true
  } finally {
    loading.value = false
  }
}

async function register() {
  errorMsg.value = ''
  registering.value = true
  try {
    const { data: opts } = await authApi.passkeyRegisterBegin()
    const prepared = { publicKey: prepareRegistrationOptions(opts) }
    const credential = await navigator.credentials.create(prepared)
    if (!credential) throw new Error('Abgebrochen')
    const serialized = {
      ...serializeRegistrationCredential(credential),
      name: newName.value.trim() || 'Passkey',
    }
    await authApi.passkeyRegisterComplete(serialized)
    ui.success('Passkey registriert')
    adding.value = false
    newName.value = ''
    await load()
  } catch (e) {
    if (e.name === 'NotAllowedError') {
      errorMsg.value = 'Registrierung abgebrochen'
    } else if (e.name === 'SecurityError') {
      errorMsg.value = 'Passkeys erfordern HTTPS (außer auf localhost)'
    } else if (e.name === 'InvalidStateError') {
      errorMsg.value = 'Dieser Passkey ist bereits registriert'
    } else if (e.response?.data?.error) {
      errorMsg.value = e.response.data.error
    } else {
      errorMsg.value = e.message || 'Registrierung fehlgeschlagen'
    }
  } finally {
    registering.value = false
  }
}

async function remove(cred) {
  const ok = await ui.confirm({
    title: 'Passkey löschen',
    message: `„${cred.name}" wirklich löschen? Du kannst dich dann nicht mehr damit anmelden.`,
    danger: true,
  })
  if (!ok) return
  try {
    await authApi.passkeyDelete(cred.id)
    ui.success('Passkey gelöscht')
    await load()
  } catch (e) {
    ui.error(e.response?.data?.error || 'Löschen fehlgeschlagen')
  }
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>
