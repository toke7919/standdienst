<template>
  <div class="max-w-2xl mx-auto px-4 py-12">
    <h1 class="text-2xl font-bold text-gray-900 mb-8">Datenschutzerklärung</h1>
    <div
      v-if="html"
      class="prose prose-sm max-w-none text-gray-700"
      v-html="html"
    />
    <p v-else class="text-gray-500">Keine Datenschutzerklärung hinterlegt.</p>
    <button class="mt-8 btn-secondary" @click="$router.back()">Zurück</button>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'

const route = useRoute()
const instanceStore = useInstanceStore()

const html = computed(() => instanceStore.current?.settings?.privacy_policy_html || null)

onMounted(() => {
  if (!instanceStore.current && route.params.slug) {
    instanceStore.loadInstance(route.params.slug)
  }
})
</script>
