<template>
  <div class="min-h-dvh flex flex-col bg-linear-to-b from-primary-800 via-primary-700 to-primary-600">

    <!-- Branding -->
    <div class="shrink-0 pt-14 pb-32 px-6 text-white text-center">
      <div class="mb-5">
        <img
          v-if="settings?.logo_filename"
          :src="`/uploads/${settings.logo_filename}`"
          class="h-20 object-contain mx-auto drop-shadow-xl"
          alt="Logo"
        />
        <img v-else src="/assets/mark-ticket.svg" class="w-20 h-20 mx-auto drop-shadow-xl" alt="Standdienst" />
      </div>
      <h1 class="text-2xl font-bold tracking-tight">{{ settings?.site_title || 'Standdienst' }}</h1>
      <p class="text-primary-200 mt-1.5 text-sm">Helfer-Verwaltung</p>
    </div>

    <!-- Card – überlappt den Branding-Bereich -->
    <div class="flex-1 bg-soft rounded-t-4xl shadow-2xl -mt-20 overflow-y-auto">
      <div class="max-w-md mx-auto px-6 pt-8 pb-10">

        <!-- Instanz nicht gefunden -->
        <div v-if="instanceStore.notFound" class="rounded-md text-center text-red-800 bg-red-50 border border-red-200 p-6">
          <p class="font-semibold text-base mb-1">Seite nicht gefunden</p>
          <p class="text-sm text-red-700">Die aufgerufene Seite existiert nicht.</p>
          <RouterLink to="/" class="inline-block mt-4 text-sm text-red-600 hover:text-red-800 underline">← Zur Startseite</RouterLink>
        </div>

        <!-- Gesperrt -->
        <div v-else-if="settings?.site_locked" class="rounded-md text-center text-amber-800 bg-amber-50 border border-amber-200 p-5">
          <p class="font-semibold">Anmeldung gesperrt</p>
          <p v-if="settings.lock_message" class="text-sm mt-1">{{ settings.lock_message }}</p>
        </div>

        <template v-else>
          <!-- Login-Formular -->
          <div>
            <form @submit.prevent="submit" class="space-y-3">
              <div>
                <label class="label">E-Mail</label>
                <input
                  v-model="form.email"
                  type="email"
                  class="input"
                  required
                  autocomplete="email"
                  inputmode="email"
                />
              </div>
              <div>
                <label class="label">Passwort</label>
                <input
                  v-model="form.password"
                  type="password"
                  class="input"
                  required
                  autocomplete="current-password"
                />
              </div>
              <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
              <button
                type="submit"
                class="btn-primary w-full flex items-center justify-center gap-2"
                :disabled="loading"
              >
                <LoadingSpinner v-if="loading" size="sm" />
                Einloggen
              </button>
            </form>

            <div class="text-center mt-3 space-y-2">
              <RouterLink :to="`/${slug}/forgot-password`" class="block text-sm text-muted hover:text-ink/80">
                Passwort vergessen?
              </RouterLink>
              <RouterLink :to="`/${slug}/register`" class="block text-sm text-muted hover:text-ink/80">
                Noch nicht eingetragen? → Hier eintragen
              </RouterLink>
            </div>
          </div>
        </template>

        <!-- Footer -->
        <footer class="mt-10 text-center text-xs text-muted space-y-1">
          <div class="flex justify-center gap-4">
            <RouterLink
              :to="instanceStore.notFound ? '/impressum' : `/${slug}/impressum`"
              class="hover:text-ink/80"
            >Impressum</RouterLink>
            <RouterLink
              v-if="!instanceStore.notFound && settings?.has_privacy_policy"
              :to="`/${slug}/datenschutz`"
              class="hover:text-ink/80"
            >Datenschutz</RouterLink>
          </div>
          <p v-if="footerCopyright">{{ footerCopyright }}</p>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
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

const footerCopyright = computed(() =>
  instanceStore.notFound
    ? (instanceStore.globalInfo?.copyright_text || '')
    : (settings.value?.copyright_text || '')
)

onMounted(() => {
  instanceStore.loadInstance(slug.value)
})

watch(() => instanceStore.notFound, (val) => {
  if (val) instanceStore.loadGlobalInfo()
})

async function submit() {
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.volunteerLogin(slug.value, form.value.email, form.value.password)
    router.push(`/${slug.value}`)
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Anmeldung fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>
