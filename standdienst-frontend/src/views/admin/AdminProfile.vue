<template>
  <div class="max-w-lg space-y-6">
    <h1 class="text-2xl font-bold text-ink">Profil bearbeiten</h1>

    <!-- Stammdaten -->
    <div class="card space-y-4">
      <h2 class="text-base font-semibold text-ink">Persönliche Daten</h2>
      <form @submit.prevent="saveProfile" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Vorname</label>
            <input v-model="profileForm.first_name" class="input" autocomplete="given-name" />
          </div>
          <div>
            <label class="label">Nachname</label>
            <input v-model="profileForm.last_name" class="input" autocomplete="family-name" />
          </div>
        </div>
        <div>
          <label class="label">E-Mail</label>
          <input v-model="profileForm.email" type="email" class="input" required autocomplete="email" />
        </div>
        <div>
          <label class="label">
            Neues Passwort
            <span class="text-muted font-normal text-xs">(leer lassen zum Beibehalten)</span>
          </label>
          <div class="relative">
            <input
              v-model="profileForm.password"
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
        <div v-if="profileForm.password">
          <label class="label">Passwort bestätigen</label>
          <input v-model="profileForm.passwordConfirm" type="password" class="input" autocomplete="new-password" />
          <p v-if="profileForm.passwordConfirm && profileForm.password !== profileForm.passwordConfirm" class="text-xs text-red-500 mt-1">
            Passwörter stimmen nicht überein
          </p>
        </div>
        <p v-if="profileError" class="text-sm text-red-600">{{ profileError }}</p>
        <button type="submit" class="btn-primary" :disabled="profileSaving">
          <LoadingSpinner v-if="profileSaving" size="sm" class="mr-2" />
          Speichern
        </button>
      </form>
    </div>

    <!-- Benachrichtigungen: Tages-Digest per Instanz -->
    <div v-if="digestInstances.length > 0" class="card space-y-4">
      <div>
        <h2 class="text-base font-semibold text-ink">Tages-Digest</h2>
        <p class="text-xs text-muted mt-1">
          Täglich um 06:00 Uhr eine Zusammenfassung der Anmeldungen, Abmeldungen und Essensspenden des Vortags.
        </p>
      </div>
      <div class="space-y-3">
        <label
          v-for="inst in digestInstances"
          :key="inst.id"
          class="flex items-center justify-between gap-3 cursor-pointer"
        >
          <span class="text-sm text-ink/80">{{ inst.name }}</span>
          <div class="relative flex-shrink-0">
            <input
              type="checkbox"
              class="sr-only peer"
              :checked="inst.digest_enabled"
              @change="toggleDigest(inst)"
            />
            <div class="w-10 h-6 bg-sand rounded-full peer-checked:bg-primary-600 transition-colors"></div>
            <div class="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4"></div>
          </div>
        </label>
      </div>
    </div>

    <!-- 2FA -->
    <div class="card space-y-4">
      <div class="flex items-center gap-2">
        <h2 class="text-base font-semibold text-ink">Zwei-Faktor-Authentifizierung</h2>
        <span v-if="auth.user?.totp_enabled" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-medium">
          <ShieldCheckIcon class="w-3 h-3" />Aktiv
        </span>
      </div>

      <template v-if="!auth.user?.totp_enabled">
        <template v-if="!twoFaSetupData">
          <p class="text-sm text-ink/80">
            2FA schützt dein Konto durch einen zusätzlichen Code aus einer Authenticator-App
            (z.B. Google Authenticator, Authy).
          </p>
          <button class="btn-primary" :disabled="twoFaLoading" @click="start2fa">
            <LoadingSpinner v-if="twoFaLoading" size="sm" class="mr-1" />
            2FA einrichten
          </button>
        </template>
        <template v-else>
          <div>
            <p class="text-sm font-medium text-ink/80 mb-2">QR-Code scannen:</p>
            <img :src="qrUrl" alt="QR-Code" class="w-48 h-48 border border-sand rounded-lg" />
          </div>
          <div>
            <p class="text-sm text-muted mb-1">Oder manuell eingeben:</p>
            <code class="text-xs bg-bg-brand px-2 py-1 rounded font-mono">{{ twoFaSetupData.secret }}</code>
          </div>
          <form @submit.prevent="confirm2fa" class="space-y-3">
            <div>
              <label class="label">Code aus der App</label>
              <input v-model="twoFaCode" type="text" inputmode="numeric" maxlength="6" class="input" required />
            </div>
            <p v-if="twoFaError" class="text-sm text-red-600">{{ twoFaError }}</p>
            <button type="submit" class="btn-primary" :disabled="twoFaConfirming || twoFaCode.length < 6">
              <LoadingSpinner v-if="twoFaConfirming" size="sm" class="mr-1" />
              Bestätigen
            </button>
          </form>
        </template>
      </template>
      <template v-else>
        <p class="text-sm text-ink/80">
          2FA ist aktiv. Jede Anmeldung erfordert einen Code aus deiner Authenticator-App.
        </p>
        <button class="btn-danger" :disabled="twoFaDisabling" @click="disable2fa">
          <LoadingSpinner v-if="twoFaDisabling" size="sm" class="mr-1" />
          2FA deaktivieren
        </button>
      </template>
    </div>

    <!-- Backup-Codes-Modal -->
    <Teleport to="body">
      <div v-if="showBackupCodesModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
        <div class="bg-soft rounded-xl shadow-2xl w-full max-w-md p-6 space-y-4">
          <div class="flex items-start gap-3">
            <div class="flex-shrink-0 w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
              <KeyIcon class="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h3 class="text-base font-semibold text-ink">Backup-Codes speichern</h3>
              <p class="text-sm text-muted mt-0.5">
                Bewahre diese Codes sicher auf. Du kannst sie bei verlorenem Zugriff auf deine
                Authenticator-App verwenden. Jeder Code ist einmalig verwendbar.
              </p>
            </div>
          </div>

          <div class="bg-bg-brand border border-sand rounded-lg p-3 font-mono text-sm space-y-1">
            <div v-for="code in backupCodes" :key="code" class="tracking-widest text-ink">{{ code }}</div>
          </div>

          <div class="flex gap-2">
            <button type="button" class="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1" @click="copyBackupCodes">
              <ClipboardIcon class="w-3.5 h-3.5" />Kopieren
            </button>
            <button type="button" class="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1" @click="downloadBackupCodes">
              <ArrowDownTrayIcon class="w-3.5 h-3.5" />Herunterladen
            </button>
          </div>

          <label class="flex items-start gap-2 cursor-pointer">
            <input type="checkbox" v-model="codesAcknowledged" class="mt-0.5 rounded border-sand" />
            <span class="text-sm text-ink/80">Ich habe die Codes sicher gespeichert.</span>
          </label>

          <button type="button" class="btn-primary w-full" :disabled="!codesAcknowledged" @click="finishSetup">
            Fertig
          </button>
        </div>
      </div>
    </Teleport>

    <!-- Passkeys -->
    <div class="card space-y-4">
      <div class="flex items-center gap-2">
        <h2 class="text-base font-semibold text-ink">Passkeys</h2>
        <span v-if="credentials.length" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-medium">
          <ShieldCheckIcon class="w-3 h-3" />{{ credentials.length }} registriert
        </span>
      </div>
      <p class="text-sm text-ink/80">
        Passkeys ermöglichen passwortlose Anmeldung mit Fingerabdruck, Gesichtserkennung oder PIN.
      </p>

      <div v-if="!passkeySupported" class="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800">
        Passkeys sind in diesem Kontext nicht verfügbar.
        {{ !window.isSecureContext ? 'Passkeys erfordern HTTPS (außer auf localhost).' : 'Dein Browser unterstützt keine Passkeys.' }}
      </div>

      <div v-if="credentials.length > 0" class="space-y-2">
        <div v-for="cred in credentials" :key="cred.id"
             class="flex items-center justify-between rounded-lg border border-sand px-3 py-2">
          <div>
            <p class="text-sm font-medium text-ink">{{ cred.name }}</p>
            <p class="text-xs text-muted">
              Erstellt: {{ formatDate(cred.created_at) }}
              <span v-if="cred.last_used_at"> · Zuletzt: {{ formatDate(cred.last_used_at) }}</span>
            </p>
          </div>
          <button class="text-red-500 hover:text-red-700 p-1" title="Löschen" @click="removePasskey(cred)">
            <TrashIcon class="w-4 h-4" />
          </button>
        </div>
      </div>
      <p v-else-if="passkeysLoaded" class="text-sm text-muted">Noch keine Passkeys registriert.</p>

      <div v-if="passkeySupported && credentials.length < 5">
        <div v-if="!addingPasskey">
          <button class="btn-primary" :disabled="passkeysLoading" @click="addingPasskey = true">
            <KeyIcon class="w-4 h-4 mr-1" />
            Passkey hinzufügen
          </button>
        </div>
        <div v-else class="space-y-3">
          <div>
            <label class="label">Name (optional)</label>
            <input v-model="newPasskeyName" type="text" class="input" placeholder="z.B. MacBook, iPhone" maxlength="100" />
          </div>
          <p v-if="passkeyError" class="text-sm text-red-600">{{ passkeyError }}</p>
          <div class="flex gap-2">
            <button class="btn-primary" :disabled="passkeyRegistering" @click="registerPasskey">
              <LoadingSpinner v-if="passkeyRegistering" size="sm" class="mr-1" />
              Registrieren
            </button>
            <button class="btn-secondary" @click="addingPasskey = false; passkeyError = ''">Abbrechen</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { authApi } from '@/api/auth'
import { adminApi } from '@/api/admin'
import { EyeIcon, EyeSlashIcon, ShieldCheckIcon, KeyIcon, TrashIcon, ClipboardIcon, ArrowDownTrayIcon } from '@heroicons/vue/24/outline'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { prepareRegistrationOptions, serializeRegistrationCredential } from '@/utils/webauthn'

const auth = useAuthStore()
const ui = useUiStore()

// ── Tages-Digest ───────────────────────────────────────────────────────────
const digestInstances = ref([])

async function loadDigestInstances() {
  const u = auth.user
  if (!u) return
  if (u.role === 'organizer') {
    digestInstances.value = (u.instances || []).map(i => ({
      id: i.id, name: i.name, slug: i.slug,
      digest_enabled: i.digest_enabled ?? true,
    }))
  } else if (u.role === 'admin') {
    const res = await adminApi.getInstances({ per_page: 200 })
    const subIds = new Set(u.digest_subscription_ids || [])
    digestInstances.value = (res.data.data || []).map(i => ({
      id: i.id, name: i.name, slug: i.slug,
      digest_enabled: subIds.has(i.id),
    }))
  }
}

async function toggleDigest(inst) {
  inst.digest_enabled = !inst.digest_enabled
  try {
    const u = auth.user
    if (u.role === 'organizer') {
      await authApi.updateProfile({
        digest_prefs: digestInstances.value.map(i => ({
          instance_id: i.id,
          digest_enabled: i.digest_enabled,
        })),
      })
    } else {
      await authApi.updateProfile({
        digest_subscription_ids: digestInstances.value
          .filter(i => i.digest_enabled)
          .map(i => i.id),
      })
    }
    ui.success(inst.digest_enabled ? 'Digest aktiviert' : 'Digest deaktiviert')
    await auth.fetchMe()
  } catch (e) {
    inst.digest_enabled = !inst.digest_enabled
    ui.err(e.response?.data?.error || 'Fehler')
  }
}

// ── Profil ─────────────────────────────────────────────────────────────────
const profileForm = ref({
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  passwordConfirm: '',
})
const profileSaving = ref(false)
const profileError = ref('')
const showPw = ref(false)

async function saveProfile() {
  profileError.value = ''
  if (profileForm.value.password && profileForm.value.password !== profileForm.value.passwordConfirm) {
    profileError.value = 'Passwörter stimmen nicht überein'
    return
  }
  profileSaving.value = true
  const data = {
    first_name: profileForm.value.first_name,
    last_name: profileForm.value.last_name,
    email: profileForm.value.email,
  }
  if (profileForm.value.password) data.password = profileForm.value.password
  try {
    await authApi.updateProfile(data)
    ui.success('Gespeichert')
    profileForm.value.password = ''
    profileForm.value.passwordConfirm = ''
    await auth.fetchMe()
  } catch (e) {
    profileError.value = e.response?.data?.error || 'Fehler beim Speichern'
  } finally {
    profileSaving.value = false
  }
}

// ── 2FA ────────────────────────────────────────────────────────────────────
const twoFaSetupData = ref(null)
const twoFaCode = ref('')
const twoFaLoading = ref(false)
const twoFaConfirming = ref(false)
const twoFaDisabling = ref(false)
const twoFaError = ref('')
const backupCodes = ref([])
const showBackupCodesModal = ref(false)
const codesAcknowledged = ref(false)

const qrUrl = computed(() => {
  if (!twoFaSetupData.value?.otpauth_url) return ''
  return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(twoFaSetupData.value.otpauth_url)}`
})

async function start2fa() {
  twoFaLoading.value = true
  try {
    const res = await authApi.setup2fa()
    twoFaSetupData.value = res.data
  } finally {
    twoFaLoading.value = false
  }
}

async function confirm2fa() {
  twoFaConfirming.value = true
  twoFaError.value = ''
  try {
    const res = await authApi.confirm2fa(twoFaCode.value)
    backupCodes.value = res.data.backup_codes || []
    codesAcknowledged.value = false
    showBackupCodesModal.value = true
  } catch (e) {
    twoFaError.value = e.response?.data?.error || 'Ungültiger Code'
    twoFaCode.value = ''
  } finally {
    twoFaConfirming.value = false
  }
}

async function finishSetup() {
  showBackupCodesModal.value = false
  backupCodes.value = []
  twoFaSetupData.value = null
  twoFaCode.value = ''
  ui.success('2FA aktiviert')
  await auth.fetchMe()
}

function copyBackupCodes() {
  navigator.clipboard.writeText(backupCodes.value.join('\n'))
  ui.success('Codes kopiert')
}

function downloadBackupCodes() {
  const blob = new Blob([backupCodes.value.join('\n')], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'standdienst-backup-codes.txt'
  a.click()
  URL.revokeObjectURL(url)
}

async function disable2fa() {
  const ok = await ui.confirm({
    title: '2FA deaktivieren',
    message: '2FA wirklich deaktivieren? Dein Konto wird weniger sicher.',
    danger: true,
  })
  if (!ok) return
  twoFaDisabling.value = true
  try {
    await authApi.disable2fa()
    ui.success('2FA deaktiviert')
    await auth.fetchMe()
  } finally {
    twoFaDisabling.value = false
  }
}

// ── Passkeys ───────────────────────────────────────────────────────────────
const credentials = ref([])
const passkeysLoaded = ref(false)
const passkeysLoading = ref(false)
const passkeyRegistering = ref(false)
const addingPasskey = ref(false)
const newPasskeyName = ref('')
const passkeyError = ref('')
const passkeySupported = ref(false)

onMounted(async () => {
  passkeySupported.value = !!(
    window.PublicKeyCredential &&
    navigator.credentials?.create &&
    window.isSecureContext
  )
  await auth.fetchMe()
  const u = auth.user
  if (u) {
    profileForm.value.first_name = u.first_name || ''
    profileForm.value.last_name = u.last_name || ''
    profileForm.value.email = u.email || ''
  }
  await Promise.all([loadDigestInstances(), loadPasskeys()])
})

async function loadPasskeys() {
  passkeysLoading.value = true
  try {
    const { data } = await authApi.passkeyList()
    credentials.value = data.credentials
    passkeysLoaded.value = true
  } finally {
    passkeysLoading.value = false
  }
}

async function registerPasskey() {
  passkeyError.value = ''
  passkeyRegistering.value = true
  try {
    const { data: opts } = await authApi.passkeyRegisterBegin()
    const prepared = { publicKey: prepareRegistrationOptions(opts) }
    const credential = await navigator.credentials.create(prepared)
    if (!credential) throw new Error('Abgebrochen')
    const serialized = {
      ...serializeRegistrationCredential(credential),
      name: newPasskeyName.value.trim() || 'Passkey',
    }
    await authApi.passkeyRegisterComplete(serialized)
    ui.success('Passkey registriert')
    addingPasskey.value = false
    newPasskeyName.value = ''
    await loadPasskeys()
    await auth.fetchMe()
  } catch (e) {
    if (e.name === 'NotAllowedError') passkeyError.value = 'Registrierung abgebrochen'
    else if (e.name === 'SecurityError') passkeyError.value = 'Passkeys erfordern HTTPS (außer auf localhost)'
    else if (e.name === 'InvalidStateError') passkeyError.value = 'Dieser Passkey ist bereits registriert'
    else passkeyError.value = e.response?.data?.error || e.message || 'Registrierung fehlgeschlagen'
  } finally {
    passkeyRegistering.value = false
  }
}

async function removePasskey(cred) {
  const ok = await ui.confirm({
    title: 'Passkey löschen',
    message: `„${cred.name}" wirklich löschen? Du kannst dich dann nicht mehr damit anmelden.`,
    danger: true,
  })
  if (!ok) return
  try {
    await authApi.passkeyDelete(cred.id)
    ui.success('Passkey gelöscht')
    await loadPasskeys()
    await auth.fetchMe()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Löschen fehlgeschlagen')
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
