<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="w-14 h-14 bg-primary-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <span class="text-white text-2xl font-bold">S</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900">Admin-Anmeldung</h1>
      </div>

      <div class="card">
        <form @submit.prevent="submit" class="space-y-4">
          <div>
            <label class="label">E-Mail</label>
            <input v-model="form.email" type="email" class="input" required autocomplete="email" />
          </div>
          <div>
            <label class="label">Passwort</label>
            <input v-model="form.password" type="password" class="input" required autocomplete="current-password" />
          </div>
          <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
          <button type="submit" class="btn-primary w-full" :disabled="loading || passkeyLoading">
            <LoadingSpinner v-if="loading" size="sm" />
            Anmelden
          </button>
        </form>

        <div class="relative my-4">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-gray-200"></div>
          </div>
          <div class="relative flex justify-center text-xs text-gray-400">
            <span class="bg-white px-2">oder</span>
          </div>
        </div>

        <button
          type="button"
          class="btn-secondary w-full flex items-center justify-center gap-2"
          :disabled="loading || passkeyLoading || !passkeySupported"
          @click="loginWithPasskey"
        >
          <LoadingSpinner v-if="passkeyLoading" size="sm" />
          <KeyIcon v-else class="w-4 h-4" />
          <span>{{ passkeySupported ? 'Mit Passkey anmelden' : 'Passkeys nicht unterstützt' }}</span>
        </button>
        <p v-if="passkeyError" class="mt-2 text-sm text-red-600 text-center">{{ passkeyError }}</p>

        <div class="mt-4 text-center">
          <RouterLink to="/admin/forgot-password" class="text-sm text-primary-600 hover:underline">
            Passwort vergessen?
          </RouterLink>
        </div>
      </div>

      <div class="mt-6 text-center">
        <RouterLink to="/" class="text-sm text-gray-500 hover:text-gray-700">
          ← Zur Startseite
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { KeyIcon } from '@heroicons/vue/24/outline'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import {
  prepareAuthenticationOptions,
  serializeAuthenticationCredential,
} from '@/utils/webauthn'

const auth = useAuthStore()
const router = useRouter()
const form = ref({ email: '', password: '' })
const errorMsg = ref('')
const loading = ref(false)
const passkeyLoading = ref(false)
const passkeyError = ref('')
const passkeySupported = ref(false)

onMounted(() => {
  passkeySupported.value = !!(
    window.PublicKeyCredential &&
    navigator.credentials?.get
  )
})

async function submit() {
  errorMsg.value = ''
  loading.value = true
  try {
    const res = await auth.login(form.value.email, form.value.password)
    if (res.requires2fa) {
      router.push('/admin/login/2fa')
    } else {
      router.push('/admin/dashboard')
    }
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Anmeldung fehlgeschlagen'
  } finally {
    loading.value = false
  }
}

async function loginWithPasskey() {
  passkeyError.value = ''
  passkeyLoading.value = true
  try {
    const { data: opts } = await authApi.passkeyAuthenticateBegin()
    const prepared = prepareAuthenticationOptions(opts)
    const credential = await navigator.credentials.get(prepared)
    if (!credential) throw new Error('Abgebrochen')
    const serialized = serializeAuthenticationCredential(credential)
    const { data } = await authApi.passkeyAuthenticateComplete(serialized)
    auth.user = data.user
    router.push('/admin/dashboard')
  } catch (e) {
    if (e.name === 'NotAllowedError') {
      passkeyError.value = 'Passkey-Anmeldung abgebrochen'
    } else {
      passkeyError.value = e.response?.data?.error || 'Passkey-Anmeldung fehlgeschlagen'
    }
  } finally {
    passkeyLoading.value = false
  }
}
</script>
