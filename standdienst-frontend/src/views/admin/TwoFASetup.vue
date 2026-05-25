<template>
  <div class="max-w-md">
    <h1 class="text-2xl font-bold text-ink mb-6">Zwei-Faktor-Authentifizierung</h1>

    <div class="card space-y-6">
      <template v-if="!auth.user?.totp_enabled">

        <!-- Schritt 1: Noch nicht eingerichtet -->
        <template v-if="!setupData">
          <p class="text-sm text-ink/80">
            2FA schützt dein Konto durch einen zusätzlichen Code aus einer Authenticator-App (z.B. Google Authenticator, Authy).
          </p>
          <button class="btn-primary" :disabled="loading" @click="startSetup">
            <LoadingSpinner v-if="loading" size="sm" />
            2FA einrichten
          </button>
        </template>

        <!-- Schritt 2: QR-Code + Bestätigungscode -->
        <template v-else>
          <div>
            <p class="text-sm font-medium text-ink/80 mb-2">QR-Code scannen:</p>
            <img :src="qrUrl" alt="QR-Code" class="w-48 h-48 border border-sand rounded-lg" />
          </div>
          <div>
            <p class="text-sm text-muted mb-1">Oder manuell eingeben:</p>
            <code class="text-xs bg-bg-brand px-2 py-1 rounded font-mono">{{ setupData.secret }}</code>
          </div>
          <form @submit.prevent="confirm" class="space-y-3">
            <div>
              <label class="label">Code aus der App</label>
              <input v-model="code" type="text" inputmode="numeric" maxlength="6" class="input" required autocomplete="one-time-code" />
            </div>
            <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
            <button type="submit" class="btn-primary" :disabled="confirming || code.length < 6">
              <LoadingSpinner v-if="confirming" size="sm" />
              Bestätigen
            </button>
          </form>
        </template>

      </template>

      <!-- 2FA bereits aktiv -->
      <template v-else>
        <div class="flex items-center gap-2 text-green-700">
          <ShieldCheckIcon class="w-5 h-5" />
          <p class="font-medium">2FA ist aktiviert</p>
        </div>
        <button class="btn-danger" :disabled="disabling" @click="disable">
          <LoadingSpinner v-if="disabling" size="sm" />
          2FA deaktivieren
        </button>
      </template>
    </div>
  </div>

  <!-- Backup-Codes Modal (kein Backdrop-Close) -->
  <Teleport to="body">
    <div v-if="backupCodes.length" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
      <div class="bg-soft rounded-md shadow-2xl w-full max-w-md p-6 space-y-5">
        <div class="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p class="text-sm font-semibold text-amber-900 mb-1">Backup-Codes jetzt sichern!</p>
          <p class="text-xs text-amber-700 leading-relaxed">
            Mit diesen Codes kannst du dich anmelden, wenn du keinen Zugriff auf deine
            Authenticator-App hast. Jeder Code kann nur <strong>einmal</strong> verwendet werden.
            Sie werden dir nur jetzt einmalig angezeigt.
          </p>
        </div>

        <div class="grid grid-cols-2 gap-2">
          <code
            v-for="c in backupCodes"
            :key="c"
            class="text-sm bg-bg-brand border border-sand rounded-lg px-3 py-2 font-mono text-ink text-center tracking-widest select-all"
          >{{ c }}</code>
        </div>

        <div class="flex gap-2">
          <button type="button" class="btn-secondary flex-1" @click="downloadCodes">
            <ArrowDownTrayIcon class="w-4 h-4" />
            Download
          </button>
          <button type="button" class="btn-secondary flex-1" @click="copyAll">
            <ClipboardDocumentListIcon class="w-4 h-4" />
            Kopieren
          </button>
          <button type="button" class="btn-secondary flex-1" @click="printCodes">
            <PrinterIcon class="w-4 h-4" />
            Drucken
          </button>
        </div>

        <label class="flex items-start gap-3 cursor-pointer select-none">
          <input type="checkbox" v-model="codesConfirmed" class="mt-0.5 h-4 w-4 rounded border-sand text-primary-600 focus:ring-primary-500" />
          <span class="text-sm text-ink/80">Ich habe meine Backup-Codes an einem sicheren Ort gespeichert.</span>
        </label>

        <button class="btn-primary w-full" :disabled="!codesConfirmed" @click="finishSetup">
          Fertig
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ShieldCheckIcon, ClipboardDocumentListIcon, PrinterIcon, ArrowDownTrayIcon } from '@heroicons/vue/24/outline'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { authApi } from '@/api/auth'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const auth = useAuthStore()
const ui = useUiStore()
const setupData = ref(null)
const backupCodes = ref([])
const codesConfirmed = ref(false)
const code = ref('')
const loading = ref(false)
const confirming = ref(false)
const disabling = ref(false)
const errorMsg = ref('')

const qrUrl = computed(() => {
  if (!setupData.value?.otpauth_url) return ''
  return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(setupData.value.otpauth_url)}`
})


async function startSetup() {
  loading.value = true
  try {
    const res = await authApi.setup2fa()
    setupData.value = res.data
  } finally {
    loading.value = false
  }
}

async function confirm() {
  confirming.value = true
  errorMsg.value = ''
  try {
    const res = await authApi.confirm2fa(code.value)
    backupCodes.value = res.data.backup_codes || []
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Ungültiger Code'
    code.value = ''
  } finally {
    confirming.value = false
  }
}

async function finishSetup() {
  backupCodes.value = []
  codesConfirmed.value = false
  setupData.value = null
  await auth.fetchMe()
}

function downloadCodes() {
  const text = [
    '2FA Backup-Codes',
    `Erstellt am ${new Date().toLocaleDateString('de-DE')}`,
    'Jeder Code kann nur einmal verwendet werden.',
    '',
    ...backupCodes.value,
  ].join('\n')
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/plain' }))
  a.download = '2fa-backup-codes.txt'
  a.click()
  URL.revokeObjectURL(a.href)
}

async function copyAll() {
  try {
    await navigator.clipboard.writeText(backupCodes.value.join('\n'))
    ui.success('Codes kopiert')
  } catch { /* ignore */ }
}

function printCodes() {
  const w = window.open('', '_blank', 'width=420,height=560')
  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>2FA Backup-Codes</title>
<style>
  body { font-family: monospace; padding: 30px; color: #111; }
  h2 { font-size: 18px; margin-bottom: 6px; }
  p { font-size: 12px; color: #555; margin-bottom: 20px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
  .code { border: 1px solid #ccc; border-radius: 6px; padding: 8px 12px; font-size: 14px;
          text-align: center; letter-spacing: 0.1em; background: #f9f9f9; }
  .hint { font-size: 11px; color: #888; border-top: 1px solid #eee; padding-top: 14px; }
</style></head><body>
<h2>2FA Backup-Codes</h2>
<p>Jeder Code kann nur einmal verwendet werden. Sicher verwahren!</p>
<div class="grid">${backupCodes.value.map(c => `<div class="code">${c}</div>`).join('')}</div>
<p class="hint">Erstellt am ${new Date().toLocaleDateString('de-DE')}</p>
</body></html>`)
  w.document.close()
  w.focus()
  w.print()
}

async function disable() {
  const ok = await ui.confirm({
    title: '2FA deaktivieren',
    message: '2FA wirklich deaktivieren? Dein Konto wird weniger sicher.',
    danger: true,
  })
  if (!ok) return
  disabling.value = true
  try {
    await authApi.disable2fa()
    ui.success('2FA deaktiviert')
    await auth.fetchMe()
  } finally {
    disabling.value = false
  }
}
</script>
