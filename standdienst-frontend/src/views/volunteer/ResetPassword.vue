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
      <p class="text-primary-200 mt-1.5 text-sm">Neues Passwort setzen</p>
    </div>

    <!-- Formular -->
    <div class="flex-1 bg-soft rounded-t-3xl shadow-2xl px-6 pt-8 pb-8 -mt-8 overflow-y-auto">
      <div class="max-w-md mx-auto">

        <div v-if="!done" class="space-y-4">
          <form @submit.prevent="submit" class="space-y-4">
            <div>
              <label class="label">Neues Passwort</label>
              <div class="relative">
                <input
                  v-model="password"
                  :type="showPw ? 'text' : 'password'"
                  class="input pr-10"
                  required
                  autocomplete="new-password"
                  placeholder="Mindestens 8 Zeichen"
                />
                <button type="button" class="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink/80" @click="showPw = !showPw">
                  <EyeSlashIcon v-if="showPw" class="w-4 h-4" />
                  <EyeIcon v-else class="w-4 h-4" />
                </button>
              </div>
            </div>
            <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
            <button type="submit" class="btn-primary w-full" :disabled="loading">
              <LoadingSpinner v-if="loading" size="sm" class="mr-2" />
              Passwort setzen
            </button>
          </form>
        </div>

        <div v-else class="rounded-md text-sm text-green-800 bg-green-50 border border-green-200 p-5 text-center">
          Passwort geändert.
          <RouterLink :to="`/${slug}/login`" class="ml-1 underline font-medium">Zum Login</RouterLink>
        </div>

        <div class="mt-5 text-center">
          <RouterLink :to="`/${slug}/login`" class="text-sm text-muted hover:text-ink/80">
            ← Zurück zum Login
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

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'
import { publicApi } from '@/api/public'
import { EyeIcon, EyeSlashIcon } from '@heroicons/vue/24/outline'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const instanceStore = useInstanceStore()
const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current)

const password = ref('')
const showPw = ref(false)
const loading = ref(false)
const done = ref(false)
const errorMsg = ref('')

onMounted(() => {
  instanceStore.loadInstance(slug.value)
})

async function submit() {
  loading.value = true
  errorMsg.value = ''
  try {
    await publicApi.resetPassword(slug.value, route.query.token, password.value)
    done.value = true
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Fehler beim Zurücksetzen'
  } finally {
    loading.value = false
  }
}
</script>
