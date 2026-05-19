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
        <p class="text-gray-500 mt-1">Als Helfer registrieren</p>
      </div>

      <div v-if="settings?.site_locked" class="card text-center text-amber-800 bg-amber-50 border border-amber-200">
        <p class="font-medium">Anmeldung gesperrt</p>
        <p v-if="settings.lock_message" class="text-sm mt-1">{{ settings.lock_message }}</p>
      </div>

      <!-- Direkt eingeloggt -->
      <div v-else-if="loggedIn" class="card text-center text-green-800 bg-green-50">
        <p class="font-semibold">Registrierung erfolgreich!</p>
        <p class="text-sm mt-1">Du wirst weitergeleitet…</p>
      </div>

      <div v-else class="card">
        <form @submit.prevent="submit" class="space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Vorname <span class="text-red-500">*</span></label>
              <input v-model="form.first_name" class="input" required autocomplete="given-name" />
            </div>
            <div>
              <label class="label">Nachname <span class="text-red-500">*</span></label>
              <input v-model="form.last_name" class="input" required autocomplete="family-name" />
            </div>
          </div>

          <div>
            <label class="label">E-Mail <span class="text-gray-400 text-xs">(optional)</span></label>
            <input v-model="form.email" type="email" class="input" autocomplete="email"
                   placeholder="Für Passwort-Einrichtung per Mail" />
            <p class="text-xs text-gray-400 mt-1">
              Ohne E-Mail wirst du direkt eingeloggt (anonymer Zugang).
            </p>
          </div>

          <!-- CAPTCHA -->
          <div v-if="captcha">
            <label class="label">Sicherheitsfrage: {{ captcha.question }}</label>
            <input v-model="form.captcha_answer" type="number" class="input max-w-32" required />
          </div>

          <!-- Datenschutz-Consent – nur wenn Policy konfiguriert -->
          <div v-if="hasPrivacyPolicy" class="flex items-start gap-2">
            <input v-model="form.consent" type="checkbox" id="consent" class="mt-1" />
            <label for="consent" class="text-sm text-gray-600">
              Ich habe die
              <RouterLink :to="`/${slug}/datenschutz`" class="text-primary-600 underline" target="_blank">
                Datenschutzerklärung
              </RouterLink>
              gelesen und stimme der Verarbeitung meiner Daten zu.
            </label>
          </div>

          <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>

          <button type="submit" class="btn-primary w-full" :disabled="loading || (hasPrivacyPolicy && !form.consent)">
            <LoadingSpinner v-if="loading" size="sm" class="mr-2" />
            Registrieren
          </button>
        </form>

        <div class="mt-4 text-center">
          <RouterLink :to="`/${slug}/login`" class="text-sm text-gray-500 hover:text-gray-700">
            Bereits registriert? Anmelden
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { publicApi } from '@/api/public'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const instanceStore = useInstanceStore()
const auth = useAuthStore()
const ui = useUiStore()
const route = useRoute()
const router = useRouter()
const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current)
const hasPrivacyPolicy = computed(() => instanceStore.current?.has_privacy_policy ?? false)

const captcha = ref(null)
const form = ref({ first_name: '', last_name: '', email: '', captcha_answer: '', consent: false })
const loading = ref(false)
const errorMsg = ref('')
const loggedIn = ref(false)

onMounted(async () => {
  await instanceStore.loadInstance(slug.value)
  await loadCaptcha()
})

async function loadCaptcha() {
  const res = await publicApi.getCaptcha(slug.value)
  captcha.value = res.data
  form.value.captcha_answer = ''
}

async function submit() {
  loading.value = true
  errorMsg.value = ''
  try {
    const payload = {
      first_name: form.value.first_name,
      last_name: form.value.last_name,
      captcha_answer: parseInt(form.value.captcha_answer),
      consent: form.value.consent,
    }
    if (form.value.email) payload.email = form.value.email

    const res = await publicApi.register(slug.value, payload)

    loggedIn.value = true
    await auth.fetchMe()

    if (form.value.email) {
      ui.info('Wir haben dir einen Link zur Passwort-Einrichtung geschickt.')
    }

    router.push(`/${slug.value}/shifts`)
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Registrierung fehlgeschlagen'
    await loadCaptcha()
  } finally {
    loading.value = false
  }
}
</script>
