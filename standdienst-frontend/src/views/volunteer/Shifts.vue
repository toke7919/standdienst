<template>
  <div>
    <h1 class="text-xl font-bold text-ink mb-2">Dienste</h1>

    <p v-if="registrationDeadline && instanceStore.current?.registration_open"
       class="text-xs text-muted flex items-center gap-1 mb-4">
      <ClockIcon class="w-3.5 h-3.5 flex-shrink-0" />
      Anmeldeschluss: {{ formattedDeadline }}
    </p>
    <p v-else-if="registrationDeadline && !instanceStore.current?.registration_open"
       class="text-xs text-amber-600 flex items-center gap-1 mb-4">
      <ClockIcon class="w-3.5 h-3.5 flex-shrink-0" />
      Anmeldeschluss abgelaufen – neue Anmeldungen sind nicht mehr möglich
    </p>
    <div v-else class="mb-4" />

    <!-- Skeleton -->
    <div v-if="loading" class="space-y-6">
      <div v-for="i in 2" :key="i" class="mb-2">
        <div class="sticky top-14 -mx-4 px-4 py-2 bg-bg-brand border-b border-sand">
          <div class="h-3 w-28 bg-sand rounded animate-pulse" />
        </div>
        <div class="space-y-4 mt-3">
          <div v-for="j in 2" :key="j">
            <div class="sticky top-[5.75rem] z-[9] -mx-4 px-4 bg-bg-brand">
              <div class="rounded-t-md overflow-hidden border border-b-0 border-sand">
                <div class="h-1 bg-sand" />
                <div class="bg-soft px-4 py-2">
                  <div class="h-3.5 w-36 bg-bg-warm rounded animate-pulse" />
                </div>
              </div>
            </div>
            <div class="bg-soft rounded-b-md border border-t-0 border-sand p-4 space-y-2">
              <div v-for="k in 3" :key="k" class="rounded-xl border border-sand p-3 flex items-center justify-between gap-4">
                <div class="flex-1 space-y-2">
                  <div class="h-3.5 w-20 bg-bg-warm rounded animate-pulse" />
                  <div class="h-2 w-32 bg-bg-warm rounded animate-pulse" />
                </div>
                <div class="h-8 w-20 bg-bg-warm rounded-lg animate-pulse flex-shrink-0" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else>
      <div v-for="group in grouped" :key="group.date" class="mb-6">
        <!-- Sticky Datumsheader (unterhalb der App-Kopfleiste h-14 = 3.5rem) -->
        <div class="sticky top-14 z-10 -mx-4 px-4 py-2 bg-bg-brand border-b border-sand">
          <h2 class="text-sm font-bold uppercase tracking-wide text-muted">{{ group.date }}</h2>
        </div>

        <div class="space-y-4 mt-3">
          <div v-for="standGroup in group.stands" :key="standGroup.stand_name">
            <!-- Sticky Kartenheader: Akzentstreifen + Standname integriert -->
            <div class="sticky top-[5.75rem] z-[9] -mx-4 px-4 bg-bg-brand">
              <div class="rounded-t-md overflow-hidden border border-b-0 border-sand">
                <div class="h-1 transition-colors" :class="standGroup.allFull ? 'bg-sand' : 'bg-primary-500'" />
                <div class="bg-soft px-4 py-2 flex items-center justify-between">
                  <h3 class="text-sm font-semibold transition-colors" :class="standGroup.allFull ? 'text-muted' : 'text-primary-700'">{{ standGroup.stand_name }}</h3>
                  <span v-if="standGroup.allFull" class="text-xs text-muted font-medium">Alle Dienste voll</span>
                </div>
              </div>
            </div>

            <!-- Kartenkörper -->
            <div class="bg-soft rounded-b-md border border-t-0 border-sand p-4">
              <div class="space-y-2">
                <div
                  v-for="shift in standGroup.shifts"
                  :key="shift.id"
                  class="rounded-xl border p-3 flex items-center justify-between transition-all duration-150"
                  :class="{
                    'bg-green-50 border-green-200': shift.is_registered,
                    'border-sand bg-bg-brand/40 opacity-50': !shift.is_registered && shift.is_full,
                    'border-sand': !shift.is_registered && !shift.is_full,
                  }"
                >
                  <div class="flex-1">
                    <p class="text-sm font-medium text-ink/80">{{ shift.time_range }}</p>
                    <div class="flex items-center gap-2 mt-1.5">
                      <div class="h-1.5 bg-sand rounded-full w-24">
                        <div
                          class="h-1.5 rounded-full"
                          :class="shift.is_full ? 'bg-red-400' : 'bg-green-400'"
                          :style="{ width: `${Math.min(100, (shift.current_count / shift.max_volunteers) * 100)}%` }"
                        />
                      </div>
                      <span class="text-xs text-muted">{{ shift.current_count }}/{{ shift.max_volunteers }}</span>
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
                      class="inline-flex items-center text-sm text-muted font-medium px-3 py-1.5 rounded-lg border border-sand bg-bg-brand cursor-not-allowed select-none"
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
            </div><!-- /Kartenkörper -->
          </div>
        </div>
      </div>

      <p v-if="!grouped.length" class="text-center text-muted py-12">
        Noch keine Dienste vorhanden
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { volunteerApi } from '@/api/volunteer'
import { useUiStore } from '@/stores/ui'
import { useInstanceStore } from '@/stores/instance'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { ClockIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const ui = useUiStore()
const instanceStore = useInstanceStore()
const shifts = ref([])
const loading = ref(true)
const toggling = ref(null)

const registrationDeadline = computed(() => instanceStore.current?.registration_deadline ?? null)
const formattedDeadline = computed(() => {
  if (!registrationDeadline.value) return ''
  return new Date(registrationDeadline.value).toLocaleDateString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  })
})
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
    stands: Object.entries(stands).map(([stand_name, shifts]) => ({
      stand_name,
      shifts,
      allFull: shifts.every(s => s.is_full && !s.is_registered),
    })),
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
