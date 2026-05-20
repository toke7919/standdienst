<template>
  <div class="min-h-screen flex flex-col bg-gradient-to-b from-primary-800 to-primary-700">
    <!-- Oberer Bereich: Branding -->
    <div class="flex-shrink-0 pt-16 pb-24 px-6 text-white text-center">
      <img
        v-if="settings?.logo_filename"
        :src="`/uploads/${settings.logo_filename}`"
        class="h-16 object-contain mx-auto mb-4 drop-shadow-lg"
        alt="Logo"
      />
      <div v-else class="w-16 h-16 bg-white/20 rounded-3xl flex items-center justify-center mx-auto mb-4 border border-white/30">
        <span class="text-white text-2xl font-bold">{{ settings?.site_title?.charAt(0) || 'S' }}</span>
      </div>
      <h1 class="text-2xl font-bold tracking-tight">{{ settings?.site_title || 'Standdienst' }}</h1>
      <p class="text-primary-200 mt-1.5 text-sm">Helfer-Anmeldung</p>
    </div>

    <!-- Unterer Bereich: Formular (überlappt den Branding-Bereich) -->
    <div class="flex-1 bg-white rounded-t-3xl shadow-2xl px-6 pt-8 pb-8 -mt-8 overflow-y-auto">
      <div v-if="settings?.site_locked" class="rounded-2xl text-center text-amber-800 bg-amber-50 border border-amber-200 p-5 mb-4">
        <p class="font-medium">Anmeldung gesperrt</p>
        <p v-if="settings.lock_message" class="text-sm mt-1">{{ settings.lock_message }}</p>
      </div>

      <div v-else class="space-y-3 max-w-md mx-auto">
        <RouterLink :to="`/${slug}/register`" class="btn-primary w-full text-base py-3">
          Neu anmelden / Registrieren
        </RouterLink>

        <div class="relative my-5">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-gray-200"></div>
          </div>
          <div class="relative flex justify-center text-xs text-gray-400">
            <span class="bg-white px-3">Bereits registriert?</span>
          </div>
        </div>

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
          <button type="submit" class="btn-secondary w-full" :disabled="loading">
            <LoadingSpinner v-if="loading" size="sm" />
            Einloggen
          </button>
        </form>

        <div class="text-center pt-1">
          <RouterLink :to="`/${slug}/forgot-password`" class="text-sm text-gray-400 hover:text-gray-600">
            Passwort vergessen?
          </RouterLink>
        </div>
      </div>

      <footer v-if="settings?.impressum_html || settings?.copyright_text" class="mt-8 text-center text-xs text-gray-400 space-y-1 max-w-md mx-auto">
        <p v-if="settings?.copyright_text">{{ settings.copyright_text }}</p>
        <div v-if="settings?.impressum_html" class="flex justify-center gap-4">
          <RouterLink :to="`/${slug}/impressum`" class="hover:text-gray-600">Impressum</RouterLink>
          <RouterLink v-if="settings?.has_privacy_policy" :to="`/${slug}/datenschutz`" class="hover:text-gray-600">Datenschutz</RouterLink>
        </div>
      </footer>

      <div class="mt-4 text-center max-w-md mx-auto">
        <RouterLink to="/" class="text-sm text-gray-400 hover:text-gray-600">← Startseite</RouterLink>
      </div>
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
