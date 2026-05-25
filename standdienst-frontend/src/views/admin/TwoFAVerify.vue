<template>
  <div class="min-h-screen bg-bg-brand flex items-center justify-center p-4">
    <div class="card w-full max-w-sm">
      <h1 class="text-xl font-semibold mb-1">Zwei-Faktor-Authentifizierung</h1>
      <p class="text-sm text-muted mb-6">
        {{ useBackup ? 'Backup-Code eingeben' : 'Code aus der Authenticator-App eingeben' }}
      </p>
      <form @submit.prevent="submit" class="space-y-4">
        <input
          v-if="!useBackup"
          v-model="code"
          type="text"
          inputmode="numeric"
          maxlength="6"
          placeholder="000000"
          autocomplete="one-time-code"
          name="one-time-code"
          class="input text-2xl tracking-widest text-center"
          required
        />
        <div v-else class="space-y-1">
          <input
            v-model="code"
            type="text"
            maxlength="8"
            placeholder="XXXXXXXX"
            class="input text-xl tracking-widest text-center uppercase"
            required
          />
          <p class="text-xs text-muted text-center">8-stelliger Backup-Code (ohne Bindestriche)</p>
        </div>
        <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
        <button type="submit" class="btn-primary w-full"
                :disabled="loading || code.length < (useBackup ? 8 : 6)">
          <LoadingSpinner v-if="loading" size="sm" />
          Bestätigen
        </button>
      </form>
      <button
        type="button"
        class="mt-4 w-full text-sm text-muted hover:text-ink/80 text-center"
        @click="toggleMode"
      >
        {{ useBackup ? '← Authenticator-Code verwenden' : 'Backup-Code verwenden' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()
const code = ref('')
const errorMsg = ref('')
const loading = ref(false)
const useBackup = ref(false)

function toggleMode() {
  useBackup.value = !useBackup.value
  code.value = ''
  errorMsg.value = ''
}

async function submit() {
  loading.value = true
  try {
    const res = await auth.verify2fa(code.value)
    if (res?.backup_code_used) {
      const remaining = res.remaining_backup_codes ?? '?'
      ui.warn(`Backup-Code verwendet. Noch ${remaining} Codes verfügbar.`)
    }
    if (auth.isOrganizer && auth.user?.instances?.length === 1) {
      router.push(`/admin/${auth.user.instances[0].slug}/dashboard`)
    } else {
      router.push('/admin/dashboard')
    }
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Ungültiger Code'
    code.value = ''
  } finally {
    loading.value = false
  }
}
</script>
