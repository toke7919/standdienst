<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <img
          v-if="settings?.logo_filename"
          :src="`/uploads/${settings.logo_filename}`"
          class="h-16 object-contain mx-auto mb-4"
          alt="Logo"
        />
        <h1 class="text-2xl font-bold text-gray-900">{{ settings?.site_title || 'Standdienst' }}</h1>
        <p class="text-gray-500 mt-1">Helfer-Anmeldung</p>
      </div>

      <div v-if="settings?.site_locked" class="card text-center text-amber-800 bg-amber-50 border border-amber-200">
        <p class="font-medium">Anmeldung gesperrt</p>
        <p v-if="settings.lock_message" class="text-sm mt-1">{{ settings.lock_message }}</p>
      </div>

      <div v-else class="space-y-3">
        <RouterLink :to="`/${slug}/register`" class="btn-primary w-full flex items-center justify-center text-base py-3">
          Neu anmelden / Registrieren
        </RouterLink>

        <div class="card">
          <p class="text-sm text-gray-500 mb-3">Bereits registriert? Hier einloggen:</p>
          <form @submit.prevent="submit" class="space-y-3">
            <div>
              <label class="label">E-Mail</label>
              <input v-model="form.email" type="email" class="input" required autocomplete="email" />
            </div>
            <div>
              <label class="label">Passwort</label>
              <input v-model="form.password" type="password" class="input" required autocomplete="current-password" />
            </div>
            <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
            <button type="submit" class="btn-secondary w-full" :disabled="loading">
              <LoadingSpinner v-if="loading" size="sm" />
              Anmelden
            </button>
          </form>
          <div class="mt-3 text-right">
            <RouterLink :to="`/${slug}/forgot-password`" class="text-sm text-gray-500 hover:text-gray-700">
              Passwort vergessen?
            </RouterLink>
          </div>
        </div>
      </div>

      <div class="mt-6 text-center">
        <RouterLink to="/" class="text-sm text-gray-500 hover:text-gray-700">← Startseite</RouterLink>
      </div>

      <footer v-if="settings?.impressum_html || settings?.copyright_text" class="mt-8 text-center text-xs text-gray-400 space-y-1">
        <p v-if="settings?.copyright_text">{{ settings.copyright_text }}</p>
        <div v-if="settings?.impressum_html" class="flex justify-center gap-4">
          <RouterLink :to="`/${slug}/impressum`" class="hover:text-gray-600">Impressum</RouterLink>
          <RouterLink v-if="settings?.has_privacy_policy" :to="`/${slug}/datenschutz`" class="hover:text-gray-600">Datenschutz</RouterLink>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useInstanceStore } from '@/stores/instance'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const auth = useAuthStore()
const instanceStore = useInstanceStore()
const route = useRoute()
const router = useRouter()

const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current)
const form = ref({ email: '', password: '' })
const errorMsg = ref('')
const loading = ref(false)

onMounted(() => {
  instanceStore.loadInstance(slug.value)
})

async function submit() {
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.volunteerLogin(slug.value, form.value.email, form.value.password)
    router.push(`/${slug.value}/shifts`)
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Anmeldung fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>
