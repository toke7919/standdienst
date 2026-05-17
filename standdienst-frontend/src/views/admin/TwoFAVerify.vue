<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="card w-full max-w-sm">
      <h1 class="text-xl font-semibold mb-1">Zwei-Faktor-Authentifizierung</h1>
      <p class="text-sm text-gray-500 mb-6">Code aus der Authenticator-App eingeben</p>
      <form @submit.prevent="submit" class="space-y-4">
        <input
          v-model="code"
          type="text"
          inputmode="numeric"
          maxlength="6"
          placeholder="000000"
          class="input text-2xl tracking-widest text-center"
          required
        />
        <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
        <button type="submit" class="btn-primary w-full" :disabled="loading || code.length < 6">
          <LoadingSpinner v-if="loading" size="sm" />
          Bestätigen
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const auth = useAuthStore()
const router = useRouter()
const code = ref('')
const errorMsg = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  try {
    await auth.verify2fa(code.value)
    router.push('/admin/dashboard')
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Ungültiger Code'
    code.value = ''
  } finally {
    loading.value = false
  }
}
</script>
