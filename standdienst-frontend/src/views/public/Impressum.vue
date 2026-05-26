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
      <h1 class="text-2xl font-bold tracking-tight">{{ settings?.site_title || data?.instance_name || 'Standdienst' }}</h1>
      <p class="text-primary-200 mt-1.5 text-sm">Impressum</p>
    </div>

    <div class="flex-1 bg-soft rounded-t-md shadow-lg px-6 pt-8 pb-12 -mt-8 overflow-y-auto">
      <div class="max-w-2xl mx-auto">
        <LoadingSpinner v-if="loading" />

        <template v-else-if="data">
          <div v-if="data.html" class="prose prose-sm max-w-none mb-8">
            <h2 v-if="data.context === 'instance'" class="text-lg font-semibold text-ink mb-3">
              Inhaltlich Verantwortlicher
            </h2>
            <div v-html="data.html" />
          </div>
          <div v-if="data.operator_html" class="prose prose-sm max-w-none mb-8 pt-6 border-t border-sand">
            <h2 class="text-lg font-semibold text-ink mb-3">Technischer Betreiber</h2>
            <div v-html="data.operator_html" />
          </div>
          <p v-if="!data.html && !data.operator_html" class="text-muted">Kein Impressum hinterlegt.</p>
        </template>

        <p v-else class="text-muted">Kein Impressum hinterlegt.</p>

        <button class="mt-8 btn-secondary" @click="$router.back()">Zurück</button>
      </div>
    </div>
  </div>

  <!-- Plattform-Kontext: gleiches Layout wie Instanz-Kontext -->
  <div v-else class="min-h-screen flex flex-col bg-gradient-to-b from-primary-800 to-primary-700">
    <div class="flex-shrink-0 pt-16 pb-24 px-6 text-white text-center">
      <img src="/assets/mark-ticket.svg" class="h-16 object-contain mx-auto mb-4 drop-shadow-lg" alt="Logo" />
      <h1 class="text-2xl font-bold tracking-tight">Standdienst</h1>
      <p class="text-primary-200 mt-1.5 text-sm">Impressum</p>
    </div>

    <div class="flex-1 bg-soft rounded-t-md shadow-lg px-6 pt-8 pb-12 -mt-8 overflow-y-auto">
      <div class="max-w-2xl mx-auto">
        <LoadingSpinner v-if="loading" />

        <template v-else-if="data">
          <div v-if="data.html" class="prose prose-sm max-w-none mb-8">
            <div v-html="data.html" />
          </div>
          <div v-if="data.operator_html" class="prose prose-sm max-w-none mb-8 pt-6 border-t border-sand">
            <h2 class="text-lg font-semibold text-ink mb-3">Technischer Betreiber</h2>
            <div v-html="data.operator_html" />
          </div>
          <p v-if="!data.html && !data.operator_html" class="text-muted">Kein Impressum hinterlegt.</p>
        </template>

        <p v-else class="text-muted">Kein Impressum hinterlegt.</p>

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
const data = ref(null)
const loading = ref(true)

const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current)

watch(settings, (s) => {
  if (s?.primary_color) applyTheme(s.primary_color)
}, { immediate: true })

onMounted(async () => {
  if (slug.value) {
    instanceStore.loadInstance(slug.value).catch(() => {})
  }
  try {
    const res = slug.value
      ? await publicApi.getInstanceImpressum(slug.value)
      : await publicApi.getPlatformImpressum()
    data.value = res.data.data
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
})
</script>
