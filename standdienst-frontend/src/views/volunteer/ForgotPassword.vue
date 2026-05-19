<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-6">
        <img
          v-if="settings?.logo_filename"
          :src="`/uploads/${settings.logo_filename}`"
          class="h-16 object-contain mx-auto mb-4"
          alt="Logo"
        />
        <h1 class="text-2xl font-bold text-gray-900">{{ settings?.site_title || 'Standdienst' }}</h1>
      </div>

      <div class="card">
        <h2 class="text-lg font-semibold mb-1">Passwort vergessen</h2>
        <p class="text-sm text-gray-500 mb-6">Wir schicken dir einen Reset-Link.</p>
        <form v-if="!sent" @submit.prevent="submit" class="space-y-4">
          <div><label class="label">E-Mail</label><input v-model="email" type="email" class="input" required /></div>
          <button type="submit" class="btn-primary w-full" :disabled="loading">Senden</button>
        </form>
        <div v-else class="text-sm text-green-700 bg-green-50 rounded-lg p-4">
          Falls die Adresse bekannt ist, wurde ein Link gesendet.
        </div>
        <RouterLink :to="`/${slug}/login`" class="mt-4 block text-center text-sm text-gray-500 hover:text-gray-700">
          Zurück zum Login
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'
import { publicApi } from '@/api/public'

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
