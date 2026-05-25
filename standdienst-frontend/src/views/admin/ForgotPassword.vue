<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <img src="/assets/mark-ticket.svg" alt="Standdienst" class="h-12 mx-auto mb-4 drop-shadow-lg" />
        <h1 class="text-2xl font-bold text-white">Passwort vergessen</h1>
      </div>

      <div class="bg-soft rounded-md shadow-2xl p-8">
        <p class="text-sm text-muted mb-6">Wir schicken dir einen Reset-Link per E-Mail.</p>
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
        <RouterLink to="/admin/login" class="mt-4 block text-center text-sm text-muted hover:text-ink/80">
          Zurück zum Login
        </RouterLink>
      </div>

      <div class="mt-6 text-center">
        <RouterLink to="/" class="text-sm text-primary-300 hover:text-white transition-colors">
          ← Zur Startseite
        </RouterLink>
      </div>
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
