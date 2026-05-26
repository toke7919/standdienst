<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-bold text-ink">Meine Dienste</h1>
      <a :href="icsUrl" class="btn-secondary text-sm">
        <CalendarIcon class="w-4 h-4" />
        In Kalender exportieren
      </a>
    </div>

    <!-- Skeleton -->
    <div v-if="loading" class="space-y-6">
      <div v-for="i in 2" :key="i">
        <div class="h-3 w-24 bg-sand rounded animate-pulse mb-2 mx-1" />
        <div class="card overflow-hidden !p-0">
          <div class="h-1 bg-sand rounded-t-md" />
          <div class="divide-y divide-sand">
            <div v-for="j in 3" :key="j" class="flex items-center justify-between px-4 py-3 gap-3">
              <div class="flex-1 space-y-1.5">
                <div class="h-3.5 w-32 bg-bg-warm rounded animate-pulse" />
                <div class="h-3 w-20 bg-bg-warm rounded animate-pulse" />
              </div>
              <div class="h-5 w-5 bg-bg-warm rounded-full animate-pulse" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <template v-else-if="upcomingGroups.length || pastGroups.length">
      <!-- Kommende Dienste -->
      <div v-if="upcomingGroups.length" class="space-y-6">
        <div v-for="group in upcomingGroups" :key="group.date">
          <p class="text-xs font-bold uppercase tracking-wide text-muted mb-2 px-1">{{ group.date }}</p>
          <div class="card overflow-hidden !p-0">
            <div class="h-1 bg-primary-500 rounded-t-md" />
            <div class="divide-y divide-sand">
              <div
                v-for="reg in group.items"
                :key="reg.id"
                class="flex items-center justify-between px-4 py-3 gap-3"
              >
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-semibold text-ink truncate">{{ reg.stand_name }}</p>
                  <p class="text-xs text-muted mt-0.5">{{ reg.time_range }}</p>
                </div>
                <button
                  class="flex-shrink-0 text-sand hover:text-red-500 transition-colors"
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

      <p v-else class="text-center text-muted py-8 text-sm">Keine kommenden Dienste</p>

      <!-- Vergangene Dienste (einklappbar) -->
      <div v-if="pastGroups.length" class="mt-8">
        <button
          class="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted hover:text-ink/80 mb-3 px-1 transition-colors"
          @click="showPast = !showPast"
        >
          <ChevronDownIcon class="w-3.5 h-3.5 text-muted transition-transform duration-200" :class="showPast ? '' : '-rotate-90'" />
          Vergangene Dienste ({{ totalPast }})
        </button>

        <div v-if="showPast" class="space-y-4 opacity-50">
          <div v-for="group in pastGroups" :key="group.date">
            <p class="text-xs font-bold uppercase tracking-wide text-muted mb-2 px-1">{{ group.date }}</p>
            <div class="card overflow-hidden !p-0">
              <div class="h-1 bg-sand rounded-t-md" />
              <div class="divide-y divide-sand">
                <div
                  v-for="reg in group.items"
                  :key="reg.id"
                  class="flex items-center px-4 py-3 gap-3"
                >
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-semibold text-muted truncate">{{ reg.stand_name }}</p>
                    <p class="text-xs text-muted mt-0.5">{{ reg.time_range }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <p v-else class="text-center text-muted py-12">Noch keine Anmeldungen</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { CalendarIcon, XMarkIcon, ChevronDownIcon } from '@heroicons/vue/24/outline'
import { volunteerApi } from '@/api/volunteer'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const ui = useUiStore()
const registrations = ref([])
const loading = ref(true)
const showPast = ref(false)

const icsUrl = computed(() => `/api/volunteer/${route.params.slug}/my-registrations/ical`)

const today = new Date()
today.setHours(0, 0, 0, 0)

function isPast(dateIso) {
  if (!dateIso) return false
  return new Date(dateIso) < today
}

const grouped = computed(() => {
  const byDate = {}
  for (const r of registrations.value) {
    if (!byDate[r.date_formatted]) byDate[r.date_formatted] = { items: [], date_iso: r.date_iso }
    byDate[r.date_formatted].items.push(r)
  }
  return Object.entries(byDate)
    .map(([date, val]) => ({ date, items: val.items, date_iso: val.date_iso }))
    .sort((a, b) => a.date_iso.localeCompare(b.date_iso))
})

const upcomingGroups = computed(() => grouped.value.filter(g => !isPast(g.date_iso)))
const pastGroups = computed(() => grouped.value.filter(g => isPast(g.date_iso)))
const totalPast = computed(() => pastGroups.value.reduce((s, g) => s + g.items.length, 0))

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
    title: 'Abmelden', message: `Von dem Dienst ${reg.stand_name} abmelden?`, confirmText: 'Abmelden', danger: true,
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
