<template>
  <div class="min-h-screen flex flex-col bg-gradient-to-b from-primary-800 to-primary-700">
    <!-- Branding -->
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
      <p class="text-primary-200 mt-1.5 text-sm">Als Helfer registrieren</p>
    </div>

    <!-- Formular -->
    <div class="flex-1 bg-white rounded-t-3xl shadow-2xl px-6 pt-8 pb-8 -mt-8 overflow-y-auto">
      <div class="max-w-md mx-auto">

        <div v-if="settings?.site_locked" class="rounded-2xl text-center text-amber-800 bg-amber-50 border border-amber-200 p-5">
          <p class="font-medium">Anmeldung gesperrt</p>
          <p v-if="settings.lock_message" class="text-sm mt-1">{{ settings.lock_message }}</p>
        </div>

        <div v-else-if="loggedIn" class="rounded-2xl text-center text-green-800 bg-green-50 border border-green-200 p-5">
          <p class="font-semibold">Registrierung erfolgreich!</p>
          <p class="text-sm mt-1">Du wirst weitergeleitet…</p>
        </div>

        <form v-else @submit.prevent="submit" class="space-y-4">
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
            <p class="text-xs text-gray-400 mt-1">Ohne E-Mail wirst du direkt eingeloggt (anonymer Zugang).</p>
          </div>

          <altcha-widget
            :challengeurl="`/api/public/${slug}/captcha`"
            workerurl="/altcha-worker.js"
            :hidefooter="true"
            :hidelogo="true"
            @statechange="onAltchaStateChange"
          />

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

          <button type="submit" class="btn-primary w-full" :disabled="loading || !altchaPayload || (hasPrivacyPolicy && !form.consent)">
            <LoadingSpinner v-if="loading" size="sm" class="mr-2" />
            Registrieren
          </button>
        </form>

        <div class="mt-5 text-center">
          <RouterLink :to="`/${slug}/login`" class="text-sm text-gray-400 hover:text-gray-600">
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

const altchaPayload = ref('')
const form = ref({ first_name: '', last_name: '', email: '', consent: false })
const loading = ref(false)
const errorMsg = ref('')
const loggedIn = ref(false)

onMounted(async () => {
  await instanceStore.loadInstance(slug.value)
})

function onAltchaStateChange(ev) {
  if (ev.detail?.state === 'verified') {
    altchaPayload.value = ev.detail.payload || ''
  } else {
    altchaPayload.value = ''
  }
}

async function submit() {
  loading.value = true
  errorMsg.value = ''
  try {
    const payload = {
      first_name: form.value.first_name,
      last_name: form.value.last_name,
      altcha: altchaPayload.value,
      consent: form.value.consent,
    }
    if (form.value.email) payload.email = form.value.email

    await publicApi.register(slug.value, payload)

    loggedIn.value = true
    await auth.fetchMe()

    if (form.value.email) {
      ui.info('Wir haben dir einen Link zur Passwort-Einrichtung geschickt.')
    }

    router.push(`/${slug.value}/shifts`)
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Registrierung fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>
