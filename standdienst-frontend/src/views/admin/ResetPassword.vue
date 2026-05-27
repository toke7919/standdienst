<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <img src="/assets/mark-ticket.svg" alt="Standdienst" class="h-12 mx-auto mb-4 drop-shadow-lg" />
        <h1 class="text-2xl font-bold text-white">Neues Passwort setzen</h1>
      </div>

      <div class="bg-soft rounded-md shadow-2xl p-8">
        <form v-if="!done" @submit.prevent="submit" class="space-y-4">
          <div>
            <label class="label">Neues Passwort</label>
            <input v-model="password" type="password" class="input" required autocomplete="new-password" />
            <p class="text-xs text-muted mt-1">Mindestens 12 Zeichen, Groß-/Kleinbuchstabe, Ziffer, Sonderzeichen</p>
          </div>
          <div>
            <label class="label">Passwort bestätigen</label>
            <input v-model="passwordConfirm" type="password" class="input" required autocomplete="new-password" />
            <p v-if="passwordConfirm && password !== passwordConfirm" class="text-xs text-red-500 mt-1">
              Passwörter stimmen nicht überein
            </p>
          </div>
          <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
          <button type="submit" class="btn-primary w-full" :disabled="loading">Passwort setzen</button>
        </form>
        <div v-else class="text-sm text-green-700 bg-green-50 rounded-lg p-4">
          Passwort erfolgreich geändert.
          <RouterLink to="/admin/login" class="ml-1 underline">Zum Login</RouterLink>
        </div>
        <RouterLink to="/admin/login" class="mt-4 block text-center text-sm text-muted hover:text-ink/80">
          Zurück zum Login
        </RouterLink>
      </div>

      <div class="mt-6 text-center space-y-2">
        <RouterLink to="/" class="text-sm text-primary-300 hover:text-white transition-colors">
          ← Zur Startseite
        </RouterLink>
        <div class="flex justify-center gap-4 text-xs text-primary-400">
          <RouterLink to="/impressum" class="hover:text-white transition-colors">Impressum</RouterLink>
          <RouterLink to="/datenschutz" class="hover:text-white transition-colors">Datenschutz</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { authApi } from '@/api/auth'

const route = useRoute()
const password = ref('')
const passwordConfirm = ref('')
const loading = ref(false)
const done = ref(false)
const errorMsg = ref('')

async function submit() {
  if (password.value !== passwordConfirm.value) {
    errorMsg.value = 'Passwörter stimmen nicht überein'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    await authApi.resetPassword(route.query.token, password.value, route.query.type || 'admin')
    done.value = true
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Fehler beim Zurücksetzen'
  } finally {
    loading.value = false
  }
}
</script>
