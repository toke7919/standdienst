<template>
  <div class="min-h-dvh flex flex-col bg-gradient-to-b from-primary-800 via-primary-700 to-primary-600">

    <!-- Branding -->
    <div class="flex-shrink-0 pt-14 pb-32 px-6 text-white text-center">
      <div class="mb-5">
        <img
          v-if="settings?.logo_filename"
          :src="`/uploads/${settings.logo_filename}`"
          class="h-20 object-contain mx-auto drop-shadow-xl"
          alt="Logo"
        />
        <div v-else class="w-20 h-20 bg-white/20 rounded-3xl flex items-center justify-center mx-auto border border-white/30 shadow-xl">
          <span class="text-white text-3xl font-bold">{{ settings?.site_title?.charAt(0) || 'S' }}</span>
        </div>
      </div>
      <h1 class="text-2xl font-bold tracking-tight">{{ settings?.site_title || 'Standdienst' }}</h1>
      <p class="text-primary-200 mt-1.5 text-sm">Helfer-Verwaltung</p>
    </div>

    <!-- Card – überlappt den Branding-Bereich -->
    <div class="flex-1 bg-white rounded-t-[2rem] shadow-2xl -mt-20 overflow-y-auto">
      <div class="max-w-md mx-auto px-6 pt-8 pb-10">

        <!-- Instanz nicht gefunden -->
        <div v-if="instanceStore.notFound" class="rounded-2xl text-center text-red-800 bg-red-50 border border-red-200 p-6">
          <p class="font-semibold text-base mb-1">Seite nicht gefunden</p>
          <p class="text-sm text-red-700">Die aufgerufene Seite existiert nicht.</p>
          <RouterLink to="/" class="inline-block mt-4 text-sm text-red-600 hover:text-red-800 underline">← Zur Startseite</RouterLink>
        </div>

        <!-- Gesperrt -->
        <div v-else-if="settings?.site_locked" class="rounded-2xl text-center text-amber-800 bg-amber-50 border border-amber-200 p-5">
          <p class="font-semibold">Anmeldung gesperrt</p>
          <p v-if="settings.lock_message" class="text-sm mt-1">{{ settings.lock_message }}</p>
        </div>

        <template v-else>
          <!-- Primäre Aktion: Neu anmelden -->
          <div class="mb-6">
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Neu dabei?</p>
            <RouterLink
              :to="`/${slug}/register`"
              class="flex items-center justify-between w-full rounded-2xl bg-primary-600 text-white px-5 py-4 shadow-md hover:bg-primary-700 active:scale-[0.98] transition-all duration-150"
            >
              <div class="text-left">
                <p class="font-semibold text-base leading-tight">Jetzt registrieren</p>
                <p class="text-primary-200 text-xs mt-0.5">Kostenlos anmelden &amp; Dienste wählen</p>
              </div>
              <ChevronRightIcon class="w-5 h-5 text-primary-200 flex-shrink-0" />
            </RouterLink>
          </div>

          <!-- Trennlinie -->
          <div class="relative my-6">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-gray-100" />
            </div>
            <div class="relative flex justify-center">
              <span class="bg-white px-3 text-xs text-gray-400 font-medium">Bereits registriert?</span>
            </div>
          </div>

          <!-- Sekundäre Aktion: Login -->
          <div>
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Anmelden</p>
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
                class="btn-secondary w-full flex items-center justify-center gap-2"
                :disabled="loading"
              >
                <LoadingSpinner v-if="loading" size="sm" />
                Einloggen
              </button>
            </form>

            <div class="text-center mt-3">
              <RouterLink :to="`/${slug}/forgot-password`" class="text-sm text-gray-400 hover:text-gray-600">
                Passwort vergessen?
              </RouterLink>
            </div>
          </div>
        </template>

        <!-- Footer -->
        <footer class="mt-10 text-center text-xs text-gray-400 space-y-1">
          <div class="flex justify-center gap-4">
            <RouterLink
              :to="instanceStore.notFound ? '/impressum' : `/${slug}/impressum`"
              class="hover:text-gray-600"
            >Impressum</RouterLink>
            <RouterLink
              v-if="!instanceStore.notFound && settings?.has_privacy_policy"
              :to="`/${slug}/datenschutz`"
              class="hover:text-gray-600"
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
import { ChevronRightIcon } from '@heroicons/vue/24/outline'

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
