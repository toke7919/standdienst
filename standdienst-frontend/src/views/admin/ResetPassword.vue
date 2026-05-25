<template>
  <div class="min-h-screen bg-bg-brand flex items-center justify-center p-4">
    <div class="card w-full max-w-sm">
      <h1 class="text-xl font-semibold mb-6">Neues Passwort setzen</h1>
      <form v-if="!done" @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="label">Neues Passwort</label>
          <input v-model="password" type="password" class="input" required autocomplete="new-password" />
          <p class="text-xs text-muted mt-1">Mindestens 8 Zeichen, 1 Ziffer, 1 Sonderzeichen</p>
        </div>
        <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
        <button type="submit" class="btn-primary w-full" :disabled="loading">Passwort setzen</button>
      </form>
      <div v-else class="text-sm text-green-700 bg-green-50 rounded-lg p-4">
        Passwort erfolgreich geändert.
        <RouterLink to="/admin/login" class="ml-1 underline">Zum Login</RouterLink>
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
const loading = ref(false)
const done = ref(false)
const errorMsg = ref('')

async function submit() {
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
