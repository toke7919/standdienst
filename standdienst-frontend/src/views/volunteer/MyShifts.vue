<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-bold text-gray-900">Meine Schichten</h1>
      <a :href="icsUrl" class="btn-secondary text-sm">
        <CalendarIcon class="w-4 h-4" />
        iCal
      </a>
    </div>

    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <div v-else-if="grouped.length" class="space-y-6">
      <div v-for="group in grouped" :key="group.date">
        <p class="text-xs font-bold uppercase tracking-wide text-gray-400 mb-2 px-1">{{ group.date }}</p>

        <div class="card overflow-hidden !p-0">
          <div class="h-1 bg-primary-500 rounded-t-2xl" />
          <div class="divide-y divide-gray-100">
            <div
              v-for="reg in group.items"
              :key="reg.id"
              class="flex items-center justify-between px-4 py-3 gap-3"
            >
              <div class="flex-1 min-w-0">
                <p class="text-sm font-semibold text-gray-800 truncate">{{ reg.stand_name }}</p>
                <p class="text-xs text-gray-400 mt-0.5">{{ reg.time_range }}</p>
              </div>
              <button
                class="flex-shrink-0 text-gray-300 hover:text-red-500 transition-colors"
                title="Abmelden"
                @click="cancel(reg)"
              >
                <XMarkIcon class="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <p v-else class="text-center text-gray-400 py-12">Noch keine Anmeldungen</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { CalendarIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { volunteerApi } from '@/api/volunteer'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const registrations = ref([])
const loading = ref(true)

const icsUrl = computed(() => `/api/volunteer/${route.params.slug}/my-registrations/ical`)

const grouped = computed(() => {
  const byDate = {}
  for (const r of registrations.value) {
    if (!byDate[r.date_formatted]) byDate[r.date_formatted] = []
    byDate[r.date_formatted].push(r)
  }
  return Object.entries(byDate).map(([date, items]) => ({ date, items }))
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await volunteerApi.getMyRegistrations(route.params.slug)
    registrations.value = res.data.data
  } finally {
    loading.value = false
  }
}

async function cancel(reg) {
  const ok = await ui.confirm({
    title: 'Abmelden', message: `Von der Schicht ${reg.stand_name} abmelden?`, confirmText: 'Abmelden', danger: true,
  })
  if (!ok) return
  try {
    await volunteerApi.unregisterShift(route.params.slug, reg.shift_id)
    ui.success('Abgemeldet')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
