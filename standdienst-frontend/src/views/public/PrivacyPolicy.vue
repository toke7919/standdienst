<template>
  <div class="max-w-2xl mx-auto px-4 py-12">
    <h1 class="text-2xl font-bold text-gray-900 mb-8">Datenschutzerklärung</h1>
    <LoadingSpinner v-if="loading" />
    <div
      v-else-if="html"
      class="prose prose-sm max-w-none text-gray-700"
      v-html="html"
    />
    <p v-else class="text-gray-500">Keine Datenschutzerklärung hinterlegt.</p>
    <button class="mt-8 btn-secondary" @click="$router.back()">Zurück</button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'
import { publicApi } from '@/api/public'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const instanceStore = useInstanceStore()
const html = ref(null)
const loading = ref(true)

onMounted(async () => {
  const slug = route.params.slug
  if (!slug) { loading.value = false; return }
  if (!instanceStore.current) await instanceStore.loadInstance(slug)
  try {
    const res = await publicApi.getPrivacyPolicy(slug)
    html.value = res.data.data.privacy_policy_html || null
  } catch {
    html.value = null
  } finally {
    loading.value = false
  }
})
</script>
