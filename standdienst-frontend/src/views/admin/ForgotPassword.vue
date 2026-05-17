<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="card w-full max-w-sm">
      <h1 class="text-xl font-semibold mb-1">Passwort vergessen</h1>
      <p class="text-sm text-gray-500 mb-6">Wir schicken dir einen Reset-Link per E-Mail.</p>
      <form v-if="!sent" @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="label">E-Mail</label>
          <input v-model="email" type="email" class="input" required />
        </div>
        <button type="submit" class="btn-primary w-full" :disabled="loading">Senden</button>
      </form>
      <div v-else class="text-sm text-green-700 bg-green-50 rounded-lg p-4">
        Falls die E-Mail-Adresse bekannt ist, wurde ein Reset-Link gesendet.
      </div>
      <RouterLink to="/admin/login" class="mt-4 block text-center text-sm text-gray-500 hover:text-gray-700">
        Zurück zum Login
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { authApi } from '@/api/auth'

const email = ref('')
const loading = ref(false)
const sent = ref(false)

async function submit() {
  loading.value = true
  try {
    await authApi.forgotPassword(email.value, 'admin')
    sent.value = true
  } finally {
    loading.value = false
  }
}
</script>
