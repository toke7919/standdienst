<template>
  <!-- Instanz-Kontext: Branding wie Login/Register -->
  <div v-if="slug" class="min-h-screen flex flex-col bg-gradient-to-b from-primary-800 to-primary-700">
    <div class="flex-shrink-0 pt-16 pb-24 px-6 text-white text-center">
      <img
        v-if="settings?.logo_filename"
        :src="`/uploads/${settings.logo_filename}`"
        class="h-16 object-contain mx-auto mb-4 drop-shadow-lg"
        alt="Logo"
      />
      <img v-else src="/assets/mark-ticket.svg" class="w-16 h-16 mx-auto mb-4 drop-shadow-lg" alt="Standdienst" />
      <h1 class="text-2xl font-bold tracking-tight">{{ settings?.site_title || 'Standdienst' }}</h1>
      <p class="text-primary-200 mt-1.5 text-sm">Datenschutzerklärung</p>
    </div>

    <div class="flex-1 bg-soft rounded-t-md shadow-lg px-6 pt-8 pb-12 -mt-8 overflow-y-auto">
      <div class="max-w-2xl mx-auto">
        <LoadingSpinner v-if="loading" />
        <div v-else-if="html" class="prose prose-sm max-w-none text-ink/80" v-html="html" />
        <p v-else class="text-muted">Keine Datenschutzerklärung hinterlegt.</p>
        <button class="mt-8 btn-secondary" @click="$router.back()">Zurück</button>
      </div>
    </div>
  </div>

  <!-- Plattform-Kontext / kein Slug: gleiches Layout wie Instanz-Kontext -->
  <div v-else class="min-h-screen flex flex-col bg-gradient-to-b from-primary-800 to-primary-700">
    <div class="flex-shrink-0 pt-16 pb-24 px-6 text-white text-center">
      <img src="/assets/mark-ticket.svg" class="h-16 object-contain mx-auto mb-4 drop-shadow-lg" alt="Logo" />
      <h1 class="text-2xl font-bold tracking-tight">Standdienst</h1>
      <p class="text-primary-200 mt-1.5 text-sm">Datenschutzerklärung</p>
    </div>

    <div class="flex-1 bg-soft rounded-t-md shadow-lg px-6 pt-8 pb-12 -mt-8 overflow-y-auto">
      <div class="max-w-2xl mx-auto">
        <LoadingSpinner v-if="loading" />
        <div v-else-if="html" class="prose prose-sm max-w-none text-ink/80" v-html="html" />
        <p v-else class="text-muted">Keine Datenschutzerklärung hinterlegt.</p>
        <button class="mt-8 btn-secondary" @click="$router.back()">Zurück</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'
import { publicApi } from '@/api/public'
import { applyTheme } from '@/utils/colorPalette'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const instanceStore = useInstanceStore()
const html = ref(null)
const loading = ref(true)

const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current)

watch(settings, (s) => {
  if (s?.primary_color) applyTheme(s.primary_color)
}, { immediate: true })

onMounted(async () => {
  const s = slug.value
  if (s) {
    if (!instanceStore.current) await instanceStore.loadInstance(s).catch(() => {})
  }
  try {
    const res = s
      ? await publicApi.getPrivacyPolicy(s)
      : await publicApi.getPlatformPrivacyPolicy()
    html.value = res.data.data.privacy_policy_html || null
  } catch {
    html.value = null
  } finally {
    loading.value = false
  }
})
</script>
