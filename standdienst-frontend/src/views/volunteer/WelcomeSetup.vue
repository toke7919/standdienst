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
      <p class="text-primary-200 mt-1.5 text-sm">Konto einrichten</p>
    </div>

    <!-- Inhalt -->
    <div class="flex-1 bg-soft rounded-t-3xl shadow-2xl px-6 pt-8 pb-8 -mt-8 overflow-y-auto">
      <div class="max-w-md mx-auto">

        <!-- Laden -->
        <div v-if="loading" class="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>

        <!-- Ungültiger Link -->
        <div v-else-if="invalid" class="text-center space-y-4">
          <div class="w-14 h-14 bg-amber-100 rounded-full flex items-center justify-center mx-auto">
            <ExclamationTriangleIcon class="w-7 h-7 text-amber-500" />
          </div>
          <div>
            <p class="font-semibold text-ink">Ungültiger oder abgelaufener Link</p>
            <p class="text-sm text-muted mt-1">
              Der Einrichtungslink ist nicht mehr gültig (max. 7 Tage).<br />
              Bitte registriere dich erneut oder wende dich an die Organisatoren.
            </p>
          </div>
          <RouterLink :to="`/${slug}/register`" class="btn-secondary inline-flex">
            Zur Registrierung
          </RouterLink>
        </div>

        <!-- Erfolgreich -->
        <div v-else-if="done" class="rounded-md text-center text-green-800 bg-green-50 border border-green-200 p-5">
          <p class="font-semibold">Passwort eingerichtet!</p>
          <p class="text-sm mt-1">Du wirst weitergeleitet…</p>
        </div>

        <!-- Formular -->
        <div v-else>
          <p class="text-ink/80 mb-5">
            Hallo <span class="font-semibold">{{ volunteerName }}</span>, richte jetzt dein Passwort ein.
          </p>

          <form @submit.prevent="submit" class="space-y-4">
            <div>
              <label class="label">Passwort</label>
              <div class="relative">
                <input
                  v-model="password"
                  :type="showPw ? 'text' : 'password'"
                  class="input pr-10"
                  required
                  autocomplete="new-password"
                  placeholder="Mindestens 6 Zeichen"
                />
                <button type="button" class="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink/80" @click="showPw = !showPw">
                  <EyeSlashIcon v-if="showPw" class="w-4 h-4" />
                  <EyeIcon v-else class="w-4 h-4" />
                </button>
              </div>
              <!-- Passwortstärke -->
              <div v-if="password" class="mt-2 space-y-1">
                <div class="flex gap-1">
                  <div v-for="i in 4" :key="i" class="h-1 flex-1 rounded-full transition-colors duration-200"
                    :class="i <= pwStrength.level ? pwStrength.barColor : 'bg-sand'" />
                </div>
                <p class="text-xs" :class="pwStrength.textColor">{{ pwStrength.label }}</p>
              </div>
            </div>

            <div>
              <label class="label">Passwort wiederholen</label>
              <input v-model="passwordConfirm" type="password" class="input" required autocomplete="new-password" />
            </div>

            <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>

            <button type="submit" class="btn-primary w-full" :disabled="submitting">
              <LoadingSpinner v-if="submitting" size="sm" class="mr-2" />
              Passwort einrichten & anmelden
            </button>
          </form>
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

function calcPwStrength(pw) {
  const len = pw.length
  const hasMixed = /[A-Z]/.test(pw) && /[a-z]/.test(pw)
  const hasNum = /\d/.test(pw)
  const hasSpecial = /[^A-Za-z0-9]/.test(pw)
  const bonus = (hasMixed ? 1 : 0) + (hasNum ? 1 : 0) + (hasSpecial ? 1 : 0)
  if (len < 6) return { level: 1, barColor: 'bg-red-400', textColor: 'text-red-500', label: 'Zu kurz (mind. 6 Zeichen)' }
  if (len < 8 || bonus === 0) return { level: 2, barColor: 'bg-amber-400', textColor: 'text-amber-600', label: 'Schwach' }
  if (len < 12 || bonus < 2) return { level: 3, barColor: 'bg-yellow-400', textColor: 'text-yellow-600', label: 'Mittel' }
  return { level: 4, barColor: 'bg-green-500', textColor: 'text-green-600', label: 'Stark' }
}
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'
import { useAuthStore } from '@/stores/auth'
import { publicApi } from '@/api/public'
import { EyeIcon, EyeSlashIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const instanceStore = useInstanceStore()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const slug = computed(() => route.params.slug)
const token = computed(() => route.params.token)
const settings = computed(() => instanceStore.current)

const pwStrength = computed(() => calcPwStrength(password.value))

const loading = ref(true)
const invalid = ref(false)
const done = ref(false)
const submitting = ref(false)
const volunteerName = ref('')
const password = ref('')
const passwordConfirm = ref('')
const showPw = ref(false)
const errorMsg = ref('')

onMounted(async () => {
  await instanceStore.loadInstance(slug.value)
  try {
    const res = await publicApi.welcomeInfo(slug.value, token.value)
    volunteerName.value = res.data.data.name
  } catch {
    invalid.value = true
  } finally {
    loading.value = false
  }
})

async function submit() {
  errorMsg.value = ''
  if (password.value !== passwordConfirm.value) {
    errorMsg.value = 'Passwörter stimmen nicht überein'
    return
  }
  submitting.value = true
  try {
    await publicApi.welcomeSetup(slug.value, token.value, password.value)
    done.value = true
    await auth.fetchMe()
    router.push(`/${slug.value}`)
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Fehler beim Einrichten des Passworts'
  } finally {
    submitting.value = false
  }
}
</script>
