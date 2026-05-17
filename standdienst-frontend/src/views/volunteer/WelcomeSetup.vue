<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="w-full max-w-md">

      <div v-if="loading" class="card text-center">
        <LoadingSpinner size="lg" />
        <p class="text-gray-500 mt-3 text-sm">Link wird geprüft…</p>
      </div>

      <div v-else-if="invalid" class="card text-center">
        <p class="text-4xl mb-3">⚠️</p>
        <p class="font-semibold text-gray-900">Ungültiger oder abgelaufener Link</p>
        <p class="text-sm text-gray-500 mt-2">
          Der Einrichtungslink ist nicht mehr gültig (max. 24 Stunden).<br />
          Bitte registriere dich erneut oder wende dich an die Organisatoren.
        </p>
        <RouterLink :to="`/${slug}/register`" class="mt-5 btn-secondary inline-flex">
          Zur Registrierung
        </RouterLink>
      </div>

      <div v-else-if="done" class="card text-center text-green-800 bg-green-50">
        <p class="font-semibold">Passwort eingerichtet!</p>
        <p class="text-sm mt-1">Du wirst weitergeleitet…</p>
      </div>

      <div v-else class="card">
        <div class="text-center mb-6">
          <h1 class="text-2xl font-bold text-gray-900">{{ settings?.site_title || 'Standdienst' }}</h1>
          <p class="text-gray-500 mt-1">Hallo {{ volunteerName }}, richte dein Passwort ein</p>
        </div>

        <form @submit.prevent="submit" class="space-y-4">
          <div>
            <label class="label">Passwort</label>
            <input v-model="password" type="password" class="input" required
                   autocomplete="new-password"
                   placeholder="Mindestens 8 Zeichen" />
            <p class="text-xs text-gray-400 mt-1">Mind. 8 Zeichen, 1 Ziffer, 1 Sonderzeichen</p>
          </div>

          <div>
            <label class="label">Passwort wiederholen</label>
            <input v-model="passwordConfirm" type="password" class="input" required
                   autocomplete="new-password" />
          </div>

          <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>

          <button type="submit" class="btn-primary w-full" :disabled="submitting">
            <LoadingSpinner v-if="submitting" size="sm" class="mr-2" />
            Passwort einrichten & anmelden
          </button>
        </form>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'
import { useAuthStore } from '@/stores/auth'
import { publicApi } from '@/api/public'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const instanceStore = useInstanceStore()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const slug = computed(() => route.params.slug)
const token = computed(() => route.params.token)
const settings = computed(() => instanceStore.current?.settings)

const loading = ref(true)
const invalid = ref(false)
const done = ref(false)
const submitting = ref(false)
const volunteerName = ref('')
const password = ref('')
const passwordConfirm = ref('')
const errorMsg = ref('')

onMounted(async () => {
  if (!instanceStore.current) await instanceStore.loadInstance(slug.value)
  try {
    const res = await publicApi.welcomeInfo(slug.value, token.value)
    volunteerName.value = res.data.data.name
  } catch {
    invalid.value = true
  } finally {
    loading.value = false
  }
})

async function submit() {
  errorMsg.value = ''
  if (password.value !== passwordConfirm.value) {
    errorMsg.value = 'Passwörter stimmen nicht überein'
    return
  }
  submitting.value = true
  try {
    await publicApi.welcomeSetup(slug.value, token.value, password.value)
    done.value = true
    await auth.fetchMe()
    router.push(`/${slug.value}/shifts`)
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Fehler beim Einrichten des Passworts'
  } finally {
    submitting.value = false
  }
}
</script>
