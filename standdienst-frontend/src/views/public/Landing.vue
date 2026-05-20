<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 flex flex-col items-center justify-center p-4">
    <div class="text-center text-white mb-12">
      <h1 class="text-5xl font-bold mb-3 tracking-tight">Standdienst</h1>
      <p class="text-primary-300 text-lg">Freiwilligenverwaltung für Events</p>
    </div>

    <div v-if="loading" class="text-primary-300">Lade…</div>

    <div v-else class="grid gap-3 w-full max-w-lg">
      <div
        v-for="inst in instances"
        :key="inst.id"
        class="bg-white/95 backdrop-blur-sm rounded-2xl p-5 shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all duration-150 cursor-pointer group active:scale-[0.99]"
        @click="router.push(`/${inst.slug}/login`)"
      >
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0 group-hover:bg-primary-200 transition-colors duration-150">
            <span class="text-primary-700 font-bold text-lg">{{ inst.name.charAt(0).toUpperCase() }}</span>
          </div>
          <div class="flex-1 min-w-0">
            <h2 class="text-base font-semibold text-gray-900">{{ inst.name }}</h2>
            <p class="text-sm text-gray-400 mt-0.5">{{ inst.slug }}</p>
          </div>
          <ChevronRightIcon class="w-5 h-5 text-gray-300 group-hover:text-primary-500 transition-colors duration-150 flex-shrink-0" />
        </div>
      </div>

      <p v-if="!instances.length" class="text-center text-primary-300 py-8">
        Keine aktiven Veranstaltungen vorhanden.
      </p>
    </div>

    <div class="mt-12 flex gap-4 text-sm text-primary-400">
      <RouterLink to="/admin/login" class="hover:text-white transition-colors">Admin-Bereich</RouterLink>
      <RouterLink to="/impressum" class="hover:text-white transition-colors">Impressum</RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ChevronRightIcon } from '@heroicons/vue/24/outline'
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
