<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-gray-900">{{ settings?.site_title || 'Standdienst' }}</h1>
        <p class="text-gray-500 mt-1">Als Helfer registrieren</p>
      </div>

      <div v-if="done" class="card text-center text-green-800 bg-green-50">
        <p class="font-semibold">Registrierung erfolgreich!</p>
        <p class="text-sm mt-1">Du kannst dich jetzt anmelden.</p>
        <RouterLink :to="`/${slug}/login`" class="mt-4 btn-primary inline-flex">Zum Login</RouterLink>
      </div>

      <div v-else class="card">
        <form @submit.prevent="submit" class="space-y-4">
          <div><label class="label">Name</label><input v-model="form.name" class="input" required /></div>
          <div><label class="label">E-Mail</label><input v-model="form.email" type="email" class="input" required /></div>
          <div>
            <label class="label">Passwort</label>
            <input v-model="form.password" type="password" class="input" required autocomplete="new-password" />
            <p class="text-xs text-gray-400 mt-1">Mindestens 8 Zeichen, 1 Ziffer, 1 Sonderzeichen</p>
          </div>

          <!-- CAPTCHA -->
          <div v-if="captcha">
            <label class="label">Sicherheitsfrage: {{ captcha.question }}</label>
            <input v-model="form.captcha_answer" type="number" class="input max-w-32" required />
          </div>

          <!-- DSGVO -->
          <div class="flex items-start gap-2">
            <input v-model="form.consent" type="checkbox" id="consent" class="mt-1" required />
            <label for="consent" class="text-sm text-gray-600">
              Ich stimme der
              <RouterLink :to="`/${slug}/privacy`" class="text-primary-600 underline" target="_blank">
                Datenschutzerklärung
              </RouterLink>
              zu und erkläre mich mit der Verarbeitung meiner Daten einverstanden.
            </label>
          </div>

          <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>

          <button type="submit" class="btn-primary w-full" :disabled="loading || !form.consent">
            <LoadingSpinner v-if="loading" size="sm" />
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
import { RouterLink, useRoute } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'
import { publicApi } from '@/api/public'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const instanceStore = useInstanceStore()
const route = useRoute()
const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current?.settings)

const captcha = ref(null)
const form = ref({ name: '', email: '', password: '', captcha_answer: '', consent: false })
const loading = ref(false)
const errorMsg = ref('')
const done = ref(false)

onMounted(async () => {
  if (!instanceStore.current) await instanceStore.loadInstance(slug.value)
  const res = await publicApi.getCaptcha(slug.value)
  captcha.value = res.data
})

async function submit() {
  loading.value = true
  errorMsg.value = ''
  try {
    await publicApi.register(slug.value, {
      ...form.value,
      captcha_answer: parseInt(form.value.captcha_answer),
    })
    done.value = true
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Registrierung fehlgeschlagen'
    // Reload CAPTCHA on failure
    const res = await publicApi.getCaptcha(slug.value)
    captcha.value = res.data
    form.value.captcha_answer = ''
  } finally {
    loading.value = false
  }
}
</script>
