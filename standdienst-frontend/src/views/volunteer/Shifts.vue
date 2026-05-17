<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 mb-6">Schichten</h1>

    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <div v-else>
      <div v-for="(group, date) in grouped" :key="date" class="mb-8">
        <h2 class="text-base font-semibold text-gray-700 mb-3 sticky top-0 bg-gray-50 py-2">{{ date }}</h2>
        <div class="space-y-3">
          <div
            v-for="shift in group"
            :key="shift.id"
            class="card flex items-center justify-between p-4"
          >
            <div class="flex-1">
              <p class="font-medium text-gray-900">{{ shift.stand_name }}</p>
              <p class="text-sm text-gray-500">{{ shift.time_range }}</p>
              <div class="flex items-center gap-2 mt-1">
                <div class="h-1.5 bg-gray-200 rounded-full w-24">
                  <div
                    class="h-1.5 rounded-full"
                    :class="shift.is_full ? 'bg-red-400' : 'bg-green-400'"
                    :style="{ width: `${Math.min(100, (shift.current_count / shift.max_volunteers) * 100)}%` }"
                  />
                </div>
                <span class="text-xs text-gray-400">{{ shift.current_count }}/{{ shift.max_volunteers }}</span>
              </div>
            </div>
            <div class="ml-4">
              <button
                v-if="!shift.is_registered"
                class="btn-primary text-sm"
                :disabled="shift.is_full || toggling === shift.id"
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
      <p v-if="!Object.keys(grouped).length" class="text-center text-gray-400 py-12">
        Noch keine Schichten vorhanden
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { volunteerApi } from '@/api/volunteer'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const shifts = ref([])
const loading = ref(true)
const toggling = ref(null)

const grouped = computed(() => {
  const g = {}
  for (const s of shifts.value) {
    if (!g[s.date_formatted]) g[s.date_formatted] = []
    g[s.date_formatted].push(s)
  }
  return g
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await volunteerApi.getShifts(route.params.slug)
    shifts.value = res.data.data
  } finally {
    loading.value = false
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
