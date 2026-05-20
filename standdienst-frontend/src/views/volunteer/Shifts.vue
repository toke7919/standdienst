<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 mb-4">Schichten</h1>

    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <div v-else>
      <div v-for="group in grouped" :key="group.date" class="mb-6">
        <!-- Sticky Datumsheader (unterhalb der App-Kopfleiste h-14 = 3.5rem) -->
        <div class="sticky top-14 z-10 -mx-4 px-4 py-2 bg-gray-50 border-b border-gray-200">
          <h2 class="text-sm font-bold uppercase tracking-wide text-gray-500">{{ group.date }}</h2>
        </div>

        <div class="space-y-4 mt-3">
          <div v-for="standGroup in group.stands" :key="standGroup.stand_name" class="card overflow-hidden !p-0">
            <!-- Farbiger Akzentstreifen -->
            <div class="h-1 bg-primary-500 rounded-t-2xl" />

            <div class="p-4">
              <h3 class="text-base font-semibold text-gray-800 mb-3">{{ standGroup.stand_name }}</h3>

              <div class="space-y-2">
                <div
                  v-for="shift in standGroup.shifts"
                  :key="shift.id"
                  class="rounded-xl border p-3 flex items-center justify-between transition-all duration-150"
                  :class="{
                    'bg-green-50 border-green-200': shift.is_registered,
                    'border-gray-100 bg-gray-50/40': !shift.is_registered && shift.is_full,
                    'border-gray-100': !shift.is_registered && !shift.is_full,
                  }"
                >
                  <div class="flex-1">
                    <p class="text-sm font-medium text-gray-700">{{ shift.time_range }}</p>
                    <div class="flex items-center gap-2 mt-1.5">
                      <div class="h-1.5 bg-gray-200 rounded-full w-24">
                        <div
                          class="h-1.5 rounded-full"
                          :class="shift.is_full ? 'bg-red-400' : 'bg-green-400'"
                          :style="{ width: `${Math.min(100, (shift.current_count / shift.max_volunteers) * 100)}%` }"
                        />
                      </div>
                      <span class="text-xs text-gray-400">{{ shift.current_count }}/{{ shift.max_volunteers }}</span>
                    </div>
                    <div v-if="shift.registered_names?.length" class="mt-1.5 flex flex-wrap gap-1">
                      <span
                        v-for="name in shift.registered_names"
                        :key="name"
                        class="text-xs bg-primary-100 text-primary-700 rounded-full px-2 py-0.5"
                      >{{ name }}</span>
                    </div>
                  </div>
                  <div class="ml-4 flex-shrink-0">
                    <span
                      v-if="!shift.is_registered && shift.is_full"
                      class="inline-flex items-center text-sm text-gray-400 font-medium px-3 py-1.5 rounded-lg border border-gray-200 bg-gray-50 cursor-not-allowed select-none"
                    >Dienst voll</span>
                    <button
                      v-else-if="!shift.is_registered"
                      class="btn-primary text-sm"
                      :disabled="toggling === shift.id"
                      @click="register(shift)"
                    >
                      <LoadingSpinner v-if="toggling === shift.id" size="sm" />
                      Eintragen
                    </button>
                    <button
                      v-else
                      class="btn-secondary text-sm text-red-600 border-red-200 hover:bg-red-50"
                      :disabled="toggling === shift.id"
                      @click="unregister(shift)"
                    >
                      <LoadingSpinner v-if="toggling === shift.id" size="sm" />
                      Austragen
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <p v-if="!grouped.length" class="text-center text-gray-400 py-12">
        Noch keine Schichten vorhanden
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { volunteerApi } from '@/api/volunteer'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const shifts = ref([])
const loading = ref(true)
const toggling = ref(null)
let eventSource = null

const grouped = computed(() => {
  const byDate = {}
  for (const s of shifts.value) {
    if (!byDate[s.date_formatted]) byDate[s.date_formatted] = {}
    if (!byDate[s.date_formatted][s.stand_name]) byDate[s.date_formatted][s.stand_name] = []
    byDate[s.date_formatted][s.stand_name].push(s)
  }
  return Object.entries(byDate).map(([date, stands]) => ({
    date,
    stands: Object.entries(stands).map(([stand_name, shifts]) => ({ stand_name, shifts })),
  }))
})

onMounted(async () => {
  await load()
  startEventSource()
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})

function startEventSource() {
  const slug = route.params.slug
  eventSource = new EventSource(`/api/volunteer/${slug}/shifts/events`, { withCredentials: true })
  eventSource.onmessage = async (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.type === 'connected') return
      if (data.type === 'unavailable') {
        eventSource.close()
        eventSource = null
        return
      }
      await silentReload()
    } catch {
      // Ungültiges JSON ignorieren
    }
  }
  eventSource.onerror = () => {}
}

async function load() {
  loading.value = true
  try {
    const res = await volunteerApi.getShifts(route.params.slug)
    shifts.value = res.data.data
  } finally {
    loading.value = false
  }
}

async function silentReload() {
  try {
    const res = await volunteerApi.getShifts(route.params.slug)
    shifts.value = res.data.data
  } catch {
    // Netzwerkfehler bei stiller Aktualisierung ignorieren
  }
}

async function register(shift) {
  toggling.value = shift.id
  try {
    await volunteerApi.registerShift(route.params.slug, shift.id)
    ui.success('Erfolgreich eingetragen')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  } finally {
    toggling.value = null
  }
}

async function unregister(shift) {
  toggling.value = shift.id
  try {
    await volunteerApi.unregisterShift(route.params.slug, shift.id)
    ui.success('Ausgetragen')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  } finally {
    toggling.value = null
  }
}
</script>
