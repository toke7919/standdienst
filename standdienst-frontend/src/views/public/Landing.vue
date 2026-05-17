<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-600 to-primary-800 flex flex-col items-center justify-center p-4">
    <div class="text-center text-white mb-12">
      <h1 class="text-5xl font-bold mb-4">Standdienst</h1>
      <p class="text-primary-100 text-xl">Freiwilligenverwaltung für Events</p>
    </div>

    <div v-if="loading" class="text-white">Lade…</div>

    <div v-else class="grid gap-4 w-full max-w-2xl">
      <div
        v-for="inst in instances"
        :key="inst.id"
        class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow cursor-pointer"
        @click="router.push(`/${inst.slug}/login`)"
      >
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">{{ inst.name }}</h2>
            <p class="text-sm text-gray-500 mt-0.5">{{ inst.slug }}</p>
          </div>
          <ArrowRightIcon class="w-5 h-5 text-gray-400" />
        </div>
      </div>

      <p v-if="!instances.length" class="text-center text-primary-100 py-8">
        Keine aktiven Veranstaltungen vorhanden.
      </p>
    </div>

    <div class="mt-12 flex gap-4 text-sm text-primary-200">
      <RouterLink to="/admin/login" class="hover:text-white transition-colors">Admin-Bereich</RouterLink>
      <RouterLink to="/impressum" class="hover:text-white transition-colors">Impressum</RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRightIcon } from '@heroicons/vue/24/outline'
import { publicApi } from '@/api/public'

const router = useRouter()
const instances = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await publicApi.getInstances()
    instances.value = res.data.data
  } finally {
    loading.value = false
  }
})
</script>
