<template>
  <div class="max-w-md">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Zwei-Faktor-Authentifizierung</h1>

    <div class="card space-y-6">
      <template v-if="!auth.user?.totp_enabled">
        <template v-if="!setupData">
          <p class="text-sm text-gray-600">
            2FA schützt dein Konto durch einen zusätzlichen Code aus einer Authenticator-App (z.B. Google Authenticator, Authy).
          </p>
          <button class="btn-primary" :disabled="loading" @click="startSetup">
            <LoadingSpinner v-if="loading" size="sm" />
            2FA einrichten
          </button>
        </template>

        <template v-else>
          <div>
            <p class="text-sm font-medium text-gray-700 mb-2">QR-Code scannen:</p>
            <img :src="qrUrl" alt="QR-Code" class="w-48 h-48 border border-gray-200 rounded-lg" />
          </div>
          <div>
            <p class="text-sm text-gray-500 mb-1">Oder manuell eingeben:</p>
            <code class="text-xs bg-gray-100 px-2 py-1 rounded font-mono">{{ setupData.secret }}</code>
          </div>
          <form @submit.prevent="confirm" class="space-y-3">
            <div>
              <label class="label">Code aus der App</label>
              <input v-model="code" type="text" inputmode="numeric" maxlength="6" class="input" required />
            </div>
            <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
            <button type="submit" class="btn-primary" :disabled="confirming || code.length < 6">
              <LoadingSpinner v-if="confirming" size="sm" />
              Bestätigen
            </button>
          </form>
        </template>
      </template>

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
</template>

<script setup>
import { ref, computed } from 'vue'
import { ShieldCheckIcon } from '@heroicons/vue/24/outline'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { authApi } from '@/api/auth'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const auth = useAuthStore()
const ui = useUiStore()
const setupData = ref(null)
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
    await authApi.confirm2fa(code.value)
    ui.success('2FA aktiviert')
    await auth.fetchMe()
    setupData.value = null
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Ungültiger Code'
    code.value = ''
  } finally {
    confirming.value = false
  }
}

async function disable() {
  const ok = await ui.confirm({
    title: '2FA deaktivieren', message: '2FA wirklich deaktivieren? Dein Konto wird weniger sicher.', danger: true,
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
