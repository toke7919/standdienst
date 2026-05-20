<template>
  <div class="max-w-2xl mx-auto px-4 py-12">
    <h1 class="text-2xl font-bold text-gray-900 mb-8">Impressum</h1>

    <LoadingSpinner v-if="loading" />

    <template v-else-if="data">
      <!-- Inhaltlich Verantwortlicher (instanzspezifisch) -->
      <div v-if="data.html" class="prose prose-sm max-w-none mb-8">
        <h2 v-if="data.context === 'instance'" class="text-lg font-semibold text-gray-800 mb-3">
          Inhaltlich Verantwortlicher
        </h2>
        <div v-html="data.html" />
      </div>

      <!-- Technischer Betreiber (Plattform-Impressum) -->
      <div v-if="data.operator_html" class="prose prose-sm max-w-none mb-8 pt-6 border-t border-gray-200">
        <h2 class="text-lg font-semibold text-gray-800 mb-3">Technischer Betreiber</h2>
        <div v-html="data.operator_html" />
      </div>

      <p v-if="!data.html && !data.operator_html" class="text-gray-500">
        Kein Impressum hinterlegt.
      </p>
    </template>

    <p v-else class="text-gray-500">Kein Impressum hinterlegt.</p>

    <button class="mt-8 btn-secondary" @click="$router.back()">Zurück</button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { publicApi } from '@/api/public'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const data = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const slug = route.params.slug
    const res = slug
      ? await publicApi.getInstanceImpressum(slug)
      : await publicApi.getPlatformImpressum()
    data.value = res.data.data
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
})
</script>
