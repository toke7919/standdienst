<template>
  <div class="max-w-2xl mx-auto px-4 py-12">
    <h1 class="text-2xl font-bold text-gray-900 mb-8">Impressum</h1>

    <div v-if="providerHtml" class="prose prose-sm max-w-none mb-8">
      <h2 class="text-lg font-semibold text-gray-800 mb-3">Plattformbetreiber</h2>
      <div v-html="providerHtml" />
    </div>

    <div v-if="instanceHtml" class="prose prose-sm max-w-none">
      <h2 class="text-lg font-semibold text-gray-800 mb-3">Inhaltlich Verantwortlicher</h2>
      <div v-html="instanceHtml" />
    </div>

    <p v-if="!providerHtml && !instanceHtml" class="text-gray-500">
      Kein Impressum hinterlegt.
    </p>

    <button class="mt-8 btn-secondary" @click="$router.back()">Zurück</button>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'
import { adminApi } from '@/api/admin'
import { ref } from 'vue'

const route = useRoute()
const instanceStore = useInstanceStore()
const globalSettings = ref(null)

const instanceHtml = computed(
  () => instanceStore.current?.settings?.instance_impressum_html || null
)
const providerHtml = computed(() => globalSettings.value?.provider_impressum_html || null)

onMounted(async () => {
  if (!instanceStore.current && route.params.slug) {
    await instanceStore.loadInstance(route.params.slug)
  }
  try {
    const res = await adminApi.getGlobalSettings()
    globalSettings.value = res.data.data
  } catch { /* not logged in as admin, skip */ }
})
</script>
