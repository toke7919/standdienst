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
      <div v-else class="w-16 h-16 bg-white/20 rounded-3xl flex items-center justify-center mx-auto mb-4 border border-white/30">
        <span class="text-white text-2xl font-bold">{{ settings?.site_title?.charAt(0) || (data?.instance_name?.charAt(0) || 'S') }}</span>
      </div>
      <h1 class="text-2xl font-bold tracking-tight">{{ settings?.site_title || data?.instance_name || 'Standdienst' }}</h1>
      <p class="text-primary-200 mt-1.5 text-sm">Impressum</p>
    </div>

    <div class="flex-1 bg-white rounded-t-3xl shadow-2xl px-6 pt-8 pb-12 -mt-8 overflow-y-auto">
      <div class="max-w-2xl mx-auto">
        <LoadingSpinner v-if="loading" />

        <template v-else-if="data">
          <div v-if="data.html" class="prose prose-sm max-w-none mb-8">
            <h2 v-if="data.context === 'instance'" class="text-lg font-semibold text-gray-800 mb-3">
              Inhaltlich Verantwortlicher
            </h2>
            <div v-html="data.html" />
          </div>
          <div v-if="data.operator_html" class="prose prose-sm max-w-none mb-8 pt-6 border-t border-gray-200">
            <h2 class="text-lg font-semibold text-gray-800 mb-3">Technischer Betreiber</h2>
            <div v-html="data.operator_html" />
          </div>
          <p v-if="!data.html && !data.operator_html" class="text-gray-500">Kein Impressum hinterlegt.</p>
        </template>

        <p v-else class="text-gray-500">Kein Impressum hinterlegt.</p>

        <button class="mt-8 btn-secondary" @click="$router.back()">Zurück</button>
      </div>
    </div>
  </div>

  <!-- Plattform-Kontext: einfaches Layout -->
  <div v-else class="max-w-2xl mx-auto px-4 py-12">
    <h1 class="text-2xl font-bold text-gray-900 mb-8">Impressum</h1>

    <LoadingSpinner v-if="loading" />

    <template v-else-if="data">
      <div v-if="data.html" class="prose prose-sm max-w-none mb-8">
        <div v-html="data.html" />
      </div>
      <div v-if="data.operator_html" class="prose prose-sm max-w-none mb-8 pt-6 border-t border-gray-200">
        <h2 class="text-lg font-semibold text-gray-800 mb-3">Technischer Betreiber</h2>
        <div v-html="data.operator_html" />
      </div>
      <p v-if="!data.html && !data.operator_html" class="text-gray-500">Kein Impressum hinterlegt.</p>
    </template>

    <p v-else class="text-gray-500">Kein Impressum hinterlegt.</p>

    <button class="mt-8 btn-secondary" @click="$router.back()">Zurück</button>
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
