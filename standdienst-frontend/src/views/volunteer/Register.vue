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
      <img v-else src="/assets/mark-ticket.svg" class="w-16 h-16 mx-auto mb-4 drop-shadow-lg" alt="Standdienst" />
      <h1 class="text-2xl font-bold tracking-tight">{{ settings?.site_title || 'Standdienst' }}</h1>
      <p class="text-white/90 mt-2 text-base font-medium tracking-wide">Trag dich als Helfer ein</p>
    </div>

    <!-- Formular -->
    <div class="flex-1 bg-soft rounded-t-3xl shadow-2xl px-6 pt-8 pb-8 -mt-8 overflow-y-auto">
      <div class="max-w-md mx-auto">

        <div v-if="instanceStore.notFound" class="rounded-md text-center text-red-800 bg-red-50 border border-red-200 p-6">
          <p class="font-semibold text-base mb-1">Seite nicht gefunden</p>
          <p class="text-sm text-red-700">Die aufgerufene Seite existiert nicht.</p>
          <RouterLink to="/" class="inline-block mt-4 text-sm text-red-600 hover:text-red-800 underline">← Zur Startseite</RouterLink>
        </div>

        <div v-else-if="settings?.site_locked || settings?.registration_open === false" class="rounded-md text-center text-amber-800 bg-amber-50 border border-amber-200 p-5">
          <p class="font-medium">Anmeldung gesperrt</p>
          <p v-if="settings.lock_message" class="text-sm mt-1">{{ settings.lock_message }}</p>
          <p v-else-if="settings?.registration_open === false" class="text-sm mt-1">Der Anmeldeschluss ist abgelaufen.</p>
        </div>

        <div v-else-if="loggedIn" class="rounded-md text-center text-green-800 bg-green-50 border border-green-200 p-5">
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
            <label class="label">E-Mail <span class="text-muted text-xs">(optional)</span></label>
            <input v-model="form.email" type="email" class="input" autocomplete="email"
                   placeholder="z.B. maria@beispiel.de" />
            <p class="text-xs text-muted mt-1">
              Optional – damit kannst du dich später wieder anmelden und Erinnerungen erhalten.
              Ohne E-Mail geht's auch.
            </p>
          </div>

          <div class="altcha-hidden" aria-hidden="true">
            <altcha-widget
              :challengeurl="`/api/public/${slug}/captcha`"
              workerurl="/altcha-worker.js"
              auto="onload"
              :hidefooter="true"
              :hidelogo="true"
              :strings="altchaStrings"
              class="altcha-field"
              @statechange="onAltchaStateChange"
            />
          </div>

          <div v-if="hasPrivacyPolicy" class="flex items-start gap-2">
            <input v-model="form.consent" type="checkbox" id="consent" class="mt-1" />
            <label for="consent" class="text-sm text-ink/80">
              Ich habe die
              <RouterLink :to="`/${slug}/datenschutz`" class="text-primary-600 underline">
                Datenschutzerklärung
              </RouterLink>
              gelesen und stimme der Verarbeitung meiner Daten zu.
            </label>
          </div>

          <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>

          <button type="submit" class="btn-primary w-full" :disabled="loading || !altchaPayload || (hasPrivacyPolicy && !form.consent)">
            <LoadingSpinner v-if="loading" size="sm" class="mr-2" />
            Eintragen
          </button>
        </form>

        <div class="mt-5 text-center">
          <RouterLink :to="`/${slug}/login`" class="text-sm text-muted hover:text-ink/80">
            Bereits eingetragen? → Anmelden
          </RouterLink>
        </div>

        <footer class="mt-8 text-center text-xs text-muted space-y-1">
          <div class="flex justify-center gap-4">
            <RouterLink :to="`/${slug}/impressum`" class="hover:text-ink/80">Impressum</RouterLink>
            <RouterLink v-if="settings?.has_privacy_policy" :to="`/${slug}/datenschutz`" class="hover:text-ink/80">Datenschutz</RouterLink>
          </div>
          <p v-if="settings?.copyright_text">{{ settings.copyright_text }}</p>
        </footer>

      </div>
    </div>
  </div>
</template>

<style>
.altcha-field {
  --altcha-font-size: 0.875rem;
  --altcha-max-width: 100%;
  --altcha-padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  font-family: inherit;
  display: block;
}
/* ALTCHA läuft im Hintergrund – Widget nicht sichtbar */
.altcha-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
}
</style>

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

const altchaStrings = JSON.stringify({
  label: 'Ich bin kein Roboter',
  verified: 'Verifiziert',
  verifying: 'Bitte warten …',
  error: 'Überprüfung fehlgeschlagen',
})

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

    router.push(`/${slug.value}`)
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Registrierung fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>
