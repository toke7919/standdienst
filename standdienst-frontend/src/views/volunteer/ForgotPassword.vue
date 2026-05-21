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
      <p class="text-primary-200 mt-1.5 text-sm">Passwort zurücksetzen</p>
    </div>

    <!-- Formular -->
    <div class="flex-1 bg-white rounded-t-3xl shadow-2xl px-6 pt-8 pb-8 -mt-8 overflow-y-auto">
      <div class="max-w-md mx-auto">

        <div v-if="!sent" class="space-y-4">
          <p class="text-sm text-gray-500">Wir schicken dir einen Reset-Link an deine E-Mail-Adresse.</p>
          <form @submit.prevent="submit" class="space-y-4">
            <div>
              <label class="label">E-Mail</label>
              <input v-model="email" type="email" class="input" required autocomplete="email" />
            </div>
            <button type="submit" class="btn-primary w-full" :disabled="loading">
              <LoadingSpinner v-if="loading" size="sm" class="mr-2" />
              Link senden
            </button>
          </form>
        </div>

        <div v-else class="rounded-2xl text-sm text-green-800 bg-green-50 border border-green-200 p-5 text-center">
          Falls die Adresse bekannt ist, wurde ein Link gesendet.
        </div>

        <div class="mt-5 text-center">
          <RouterLink :to="`/${slug}/login`" class="text-sm text-gray-400 hover:text-gray-600">
            ← Zurück zum Login
          </RouterLink>
        </div>

        <footer class="mt-8 text-center text-xs text-gray-400 space-y-1">
          <p v-if="settings?.copyright_text">{{ settings.copyright_text }}</p>
          <div class="flex justify-center gap-4">
            <RouterLink :to="`/${slug}/impressum`" class="hover:text-gray-600">Impressum</RouterLink>
            <RouterLink v-if="settings?.has_privacy_policy" :to="`/${slug}/datenschutz`" class="hover:text-gray-600">Datenschutz</RouterLink>
          </div>
        </footer>

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

const route = useRoute()
const instanceStore = useInstanceStore()
const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current)
const email = ref('')
const loading = ref(false)
const sent = ref(false)

onMounted(() => {
  instanceStore.loadInstance(slug.value)
})

async function submit() {
  loading.value = true
  try {
    await publicApi.forgotPassword(slug.value, email.value)
    sent.value = true
  } finally {
    loading.value = false
  }
}
</script>
