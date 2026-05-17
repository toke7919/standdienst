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
          <button type="submit" class="btn-primary w-full" :disabled="loading">
            <LoadingSpinner v-if="loading" size="sm" />
            Anmelden
          </button>
        </form>
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
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const auth = useAuthStore()
const router = useRouter()
const form = ref({ email: '', password: '' })
const errorMsg = ref('')
const loading = ref(false)

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
</script>
