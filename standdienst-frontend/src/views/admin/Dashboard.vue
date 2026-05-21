<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">
        {{ slug ? 'Dashboard' : 'Plattform-Dashboard' }}
      </h1>
      <a
        v-if="slug"
        :href="volunteerUrl"
        target="_blank"
        rel="noopener"
        class="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700 hover:underline mt-1"
      >
        <ArrowTopRightOnSquareIcon class="w-3.5 h-3.5 flex-shrink-0" />
        {{ volunteerUrl }}
      </a>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner size="lg" />
    </div>

    <template v-else-if="data">
      <!-- ================================================================
           INSTANZ-DASHBOARD
           ================================================================ -->
      <template v-if="slug">

        <!-- ── ROW 1: Hero KPIs ─────────────────────────────────────── -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">

          <!-- Belegungsring -->
          <div class="card flex flex-col items-center">
            <p class="self-start text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 lg:mb-5">Dienstbelegung</p>

            <!-- SVG Donut -->
            <div class="relative w-28 h-28 lg:w-36 lg:h-36 mb-3 lg:mb-5">
              <svg viewBox="0 0 100 100" class="w-full h-full">
                <circle cx="50" cy="50" r="36" fill="none" stroke="#f3f4f6" stroke-width="11" />
                <circle
                  cx="50" cy="50" r="36"
                  fill="none"
                  :stroke="ringColor"
                  stroke-width="11"
                  stroke-linecap="round"
                  :stroke-dasharray="`${ringDashAnimated.toFixed(1)} ${RING_C.toFixed(1)}`"
                  transform="rotate(-90 50 50)"
                  style="transition: stroke-dasharray 0.9s cubic-bezier(0.34,1.56,0.64,1)"
                />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span class="text-2xl font-black tabular-nums leading-none" :style="`color:${ringColor}`">
                  {{ data.fill_rate }}%
                </span>
                <span class="text-[11px] text-gray-400 mt-0.5 font-medium">Belegung</span>
              </div>
            </div>

            <!-- Stacked bar Vollbesetzt / Teilbesetzt / Leer -->
            <div class="w-full h-2.5 rounded-full overflow-hidden flex mb-3">
              <div
                class="h-full bg-emerald-500 transition-all duration-700"
                :style="`width:${shiftPct(data.shifts_full)}%`"
              />
              <div
                class="h-full bg-amber-400 transition-all duration-700"
                :style="`width:${shiftPct(data.shifts_free - data.shifts_empty)}%`"
              />
              <div class="h-full bg-red-300 flex-1" />
            </div>

            <!-- Legend -->
            <div class="w-full space-y-1.5">
              <div class="flex items-center gap-2 text-xs">
                <div class="w-2.5 h-2.5 rounded-full bg-emerald-500 flex-shrink-0" />
                <span class="text-gray-500 flex-1">Vollbesetzt</span>
                <span class="font-bold tabular-nums text-gray-700">{{ data.shifts_full }}</span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <div class="w-2.5 h-2.5 rounded-full bg-amber-400 flex-shrink-0" />
                <span class="text-gray-500 flex-1">Teilbesetzt</span>
                <span class="font-bold tabular-nums text-gray-700">{{ data.shifts_free - data.shifts_empty }}</span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <div class="w-2.5 h-2.5 rounded-full bg-red-300 flex-shrink-0" />
                <span class="text-gray-500 flex-1">Leer</span>
                <span class="font-bold tabular-nums" :class="data.shifts_empty > 0 ? 'text-red-500' : 'text-gray-400'">
                  {{ data.shifts_empty }}
                </span>
              </div>
            </div>
          </div>

          <!-- Nächster Termin -->
          <div class="card flex flex-col">
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Nächster Termin</p>

            <div v-if="data.next_event" class="flex-1 flex flex-col items-center justify-center py-2">
              <template v-if="data.next_event.days_until === 0">
                <p class="text-4xl lg:text-5xl font-black text-emerald-500 mb-2">Heute!</p>
              </template>
              <template v-else>
                <div class="flex items-end gap-2 mb-2">
                  <span
                    class="text-5xl lg:text-7xl font-black tabular-nums leading-none"
                    :class="data.next_event.days_until <= 2 ? 'text-amber-500' : 'text-primary-600'"
                  >{{ data.next_event.days_until }}</span>
                  <span class="text-xl font-semibold text-gray-300 mb-2 leading-none">
                    {{ data.next_event.days_until === 1 ? 'Tag' : 'Tage' }}
                  </span>
                </div>
              </template>

              <p class="text-sm font-medium text-gray-600 text-center leading-snug">
                {{ data.next_event.date_formatted }}
              </p>
              <div
                class="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold"
                :class="data.next_event.days_until === 0
                  ? 'bg-emerald-100 text-emerald-700'
                  : data.next_event.days_until <= 2
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-primary-50 text-primary-700'"
              >
                <CalendarDaysIcon class="w-3.5 h-3.5" />
                {{ data.next_event.days_until === 0 ? 'Heute!' : data.next_event.days_until === 1 ? 'Morgen' : `In ${data.next_event.days_until} Tagen` }}
              </div>
            </div>

            <div v-else class="flex-1 flex flex-col items-center justify-center text-gray-200 py-4">
              <CalendarDaysIcon class="w-16 h-16 mb-3" />
              <p class="text-sm text-gray-400">Keine anstehenden Termine</p>
            </div>
          </div>

          <!-- Gesamtkapazität -->
          <div class="card flex flex-col">
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Gesamtkapazität</p>

            <div class="flex items-end gap-1.5 mb-3 lg:mb-5">
              <span class="text-4xl lg:text-5xl font-black tabular-nums leading-none text-gray-900">{{ data.registrations }}</span>
              <span class="text-xl text-gray-300 mb-1">/</span>
              <span class="text-xl font-semibold text-gray-400 mb-1">{{ data.total_spots }}</span>
              <span class="text-sm text-gray-400 mb-1.5">Plätze</span>
            </div>

            <!-- Gradient progress bar -->
            <div class="h-3 bg-gray-100 rounded-full overflow-hidden mb-1.5">
              <div
                class="h-full rounded-full transition-all duration-700"
                :class="capacityBarClass"
                :style="`width:${capacityRate}%`"
              />
            </div>
            <div class="flex justify-between items-center mb-5">
              <span class="text-xs text-gray-400">{{ data.registrations }} belegt</span>
              <span class="text-sm font-bold tabular-nums" :class="capacityRateTextClass">{{ capacityRate }}%</span>
            </div>

            <!-- Freie Plätze sub-stat -->
            <div class="mt-auto pt-4 border-t border-gray-50 flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                <ClockIcon class="w-4 h-4 text-blue-500" />
              </div>
              <div>
                <p class="text-lg font-black tabular-nums text-gray-800 leading-none">
                  {{ Math.max(0, (data.total_spots || 0) - data.registrations) }}
                </p>
                <p class="text-xs text-gray-400">freie Plätze</p>
              </div>
            </div>
          </div>
        </div>

        <!-- ── ROW 2: Mini Stats ─────────────────────────────────────── -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">

          <!-- Helfer -->
          <div class="card">
            <div class="flex items-start justify-between mb-3">
              <div>
                <p class="text-2xl font-black tabular-nums text-gray-900">{{ data.volunteers }}</p>
                <p class="text-sm text-gray-500 mt-0.5">Helfer</p>
              </div>
              <div class="w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
                <UsersIcon class="w-5 h-5 text-blue-600" />
              </div>
            </div>
            <span
              v-if="data.volunteers_without_shift > 0"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-xs font-medium"
            >
              <ExclamationCircleIcon class="w-3 h-3 flex-shrink-0" />
              {{ data.volunteers_without_shift }} ohne Dienst
            </span>
            <span v-else class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium">
              <CheckCircleIcon class="w-3 h-3 flex-shrink-0" />
              Alle eingeteilt
            </span>
          </div>

          <!-- Anmeldungen + 7-Tage-Sparkline -->
          <div class="card">
            <div class="flex items-start justify-between mb-3">
              <div>
                <p class="text-2xl font-black tabular-nums text-gray-900">{{ data.registrations }}</p>
                <p class="text-sm text-gray-500 mt-0.5">Anmeldungen</p>
              </div>
              <div class="w-9 h-9 rounded-xl bg-violet-100 flex items-center justify-center flex-shrink-0">
                <ClipboardDocumentListIcon class="w-5 h-5 text-violet-600" />
              </div>
            </div>
            <div v-if="data.daily_registrations?.length" class="flex items-end gap-px h-8">
              <div
                v-for="d in data.daily_registrations"
                :key="d.date"
                class="flex-1 rounded-t-[2px] transition-all duration-500"
                :class="isToday(d.date) ? 'bg-violet-500' : 'bg-violet-200'"
                :style="`height:${sparkBarPx(d.count)}px`"
              />
            </div>
            <p class="text-xs text-gray-400 mt-1">7-Tage-Trend</p>
          </div>

          <!-- Leere Schichten – Alert-Karte -->
          <div
            :class="['rounded-2xl shadow-sm border p-4 lg:p-6 transition-colors duration-300',
                     data.shifts_empty > 0 ? 'bg-red-50 border-red-200' : 'bg-white border-gray-100']"
          >
            <div class="flex items-start justify-between mb-3">
              <div>
                <p
                  class="text-2xl font-black tabular-nums"
                  :class="data.shifts_empty > 0 ? 'text-red-600' : 'text-gray-900'"
                >{{ data.shifts_empty }}</p>
                <p class="text-sm text-gray-500 mt-0.5">Dienste leer</p>
              </div>
              <div
                class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                :class="data.shifts_empty > 0 ? 'bg-red-100' : 'bg-emerald-100'"
              >
                <ExclamationCircleIcon v-if="data.shifts_empty > 0" class="w-5 h-5 text-red-500" />
                <CheckCircleIcon v-else class="w-5 h-5 text-emerald-500" />
              </div>
            </div>
            <p class="text-xs font-medium" :class="data.shifts_empty > 0 ? 'text-red-500' : 'text-emerald-600'">
              {{ data.shifts_empty > 0 ? 'Helfer gesucht!' : 'Alle besetzt' }}
            </p>
          </div>

          <!-- Essensspenden -->
          <StatCard label="Essensspenden" :value="data.food_donations" color="amber" :icon="ShoppingBagIcon" />
        </div>

        <!-- ── Auslastung je Termin ──────────────────────────────────── -->
        <div v-if="data.dates_fill?.length" class="card overflow-hidden !p-0 mb-8">
          <h2 class="text-base font-semibold text-gray-800 px-4 pt-4 pb-3">Auslastung je Termin</h2>
          <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-100 bg-gray-50">
                <th class="text-left px-4 py-2 font-medium text-gray-500">Datum</th>
                <th class="text-right px-4 py-2 font-medium text-gray-500">Dienste</th>
                <th class="text-right px-4 py-2 font-medium text-gray-500">Vollbelegt</th>
                <th class="text-right px-4 py-2 font-medium text-gray-500 pr-5">Belegung</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="d in data.dates_fill"
                :key="d.date_id"
                class="border-b border-gray-50 last:border-0 hover:bg-gray-50"
              >
                <td class="px-4 py-2.5 font-medium text-gray-900">{{ d.date_formatted }}</td>
                <td class="px-4 py-2.5 text-right text-gray-600">{{ d.shifts }}</td>
                <td class="px-4 py-2.5 text-right text-gray-600">{{ d.shifts_full }}</td>
                <td class="px-4 py-2.5 text-right pr-5">
                  <div class="inline-flex items-center gap-2">
                    <div class="w-20 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        class="h-full rounded-full"
                        :class="fillBarColor(d.fill_rate)"
                        :style="`width:${d.fill_rate}%`"
                      />
                    </div>
                    <span class="text-xs font-semibold w-9 text-right tabular-nums" :class="fillTextColor(d.fill_rate)">
                      {{ d.fill_rate }}%
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>
      </template>

      <!-- ================================================================
           GLOBALES ADMIN-DASHBOARD
           ================================================================ -->
      <template v-else>
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Instanzen" :value="data.instance_count" color="blue" :icon="ServerIcon" />
          <StatCard label="Helfer gesamt" :value="data.total_volunteers" color="emerald" :icon="UsersIcon" />
          <StatCard label="Anmeldungen" :value="data.total_registrations" color="violet" :icon="ClipboardDocumentListIcon" />
          <StatCard label="Essensspenden" :value="data.total_food_donations" color="amber" :icon="ShoppingBagIcon" />
        </div>
        <div v-if="data.instances?.length" class="card mb-8">
          <h2 class="text-base font-semibold text-gray-800 mb-4">Instanzübersicht</h2>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-gray-100">
                  <th class="text-left py-2 pr-4 font-medium text-gray-500">Instanz</th>
                  <th class="text-right py-2 px-3 font-medium text-gray-500">Helfer</th>
                  <th class="text-right py-2 px-3 font-medium text-gray-500">Dienste</th>
                  <th class="text-right py-2 px-3 font-medium text-gray-500">Anmeldungen</th>
                  <th class="text-right py-2 px-3 font-medium text-gray-500">Belegung</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="inst in data.instances"
                  :key="inst.id"
                  class="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                  @click="$router.push(`/admin/${inst.slug}/dashboard`)"
                >
                  <td class="py-2 pr-4 font-medium text-gray-900">{{ inst.name }}</td>
                  <td class="py-2 px-3 text-right text-gray-600">{{ inst.volunteers }}</td>
                  <td class="py-2 px-3 text-right text-gray-600">{{ inst.shifts }}</td>
                  <td class="py-2 px-3 text-right text-gray-600">{{ inst.registrations }}</td>
                  <td class="py-2 px-3 text-right">
                    <span :class="fillBadgeColor(inst.fill_rate)" class="text-xs font-semibold px-2 py-0.5 rounded-full">
                      {{ inst.fill_rate }}%
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <!-- ── Letzte Aktivitäten (beide Dashboards) ──────────────────── -->
      <div v-if="data.recent_activity?.length" class="card overflow-hidden !p-0">
        <h2 class="text-base font-semibold text-gray-800 px-4 pt-4 pb-3">Letzte Aktivitäten</h2>

        <!-- Mobile: gestapelte Liste (kein horizontales Overflow) -->
        <div class="md:hidden divide-y divide-gray-50">
          <div
            v-for="log in data.recent_activity"
            :key="log.id"
            class="flex items-start gap-3 px-4 py-3"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-0.5 flex-wrap">
                <EventBadge :type="log.event_type" />
                <span class="text-xs text-gray-600 truncate">{{ log.volunteer_name || '—' }}</span>
              </div>
              <p v-if="log.details" class="text-xs text-gray-400 truncate">{{ log.details }}</p>
            </div>
            <span class="text-xs text-gray-300 flex-shrink-0 mt-0.5">{{ fmtTime(log.timestamp) }}</span>
          </div>
        </div>

        <!-- Desktop: Tabelle -->
        <table class="hidden md:table w-full text-sm">
          <tbody>
            <tr
              v-for="log in data.recent_activity"
              :key="log.id"
              class="border-t border-gray-50 hover:bg-gray-50"
            >
              <td class="px-4 py-2.5 text-gray-400 whitespace-nowrap text-xs w-32 flex-shrink-0">
                {{ fmtTime(log.timestamp) }}
              </td>
              <td class="px-4 py-2.5">
                <EventBadge :type="log.event_type" />
              </td>
              <td class="px-4 py-2.5 text-gray-600 text-xs">{{ log.volunteer_name || '—' }}</td>
              <td class="px-4 py-2.5 text-gray-500 text-xs max-w-xs truncate" :title="log.details">
                {{ log.details || '' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div v-else class="text-center text-gray-400 py-16">
      Bitte eine Instanz auswählen, um das Dashboard anzuzeigen.
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, defineComponent, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { EVENT_META, fmtTime } from '@/utils/activityLog'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import {
  UsersIcon, ClockIcon, ClipboardDocumentListIcon,
  CheckCircleIcon, ShoppingBagIcon, ServerIcon,
  ExclamationCircleIcon, CalendarDaysIcon, ArrowTopRightOnSquareIcon,
} from '@heroicons/vue/24/outline'

const auth = useAuthStore()
const route = useRoute()
const data = ref(null)
const loading = ref(true)
const slug = computed(() => route.params.slug || null)
const volunteerUrl = computed(() => slug.value ? `${window.location.origin}/${slug.value}` : '')

// ── SVG Donut ──────────────────────────────────────────────────────
const RING_R = 36
const RING_C = 2 * Math.PI * RING_R          // ≈ 226.2
const ringDashAnimated = ref(0)

watch(data, (newVal) => {
  if (!newVal) { ringDashAnimated.value = 0; return }
  ringDashAnimated.value = 0
  requestAnimationFrame(() => requestAnimationFrame(() => {
    ringDashAnimated.value = ((newVal.fill_rate ?? 0) / 100) * RING_C
  }))
}, { immediate: true })

const ringColor = computed(() => {
  const r = data.value?.fill_rate ?? 0
  return r >= 80 ? '#10b981' : r >= 50 ? '#f59e0b' : '#ef4444'
})

// ── Kapazität ──────────────────────────────────────────────────────
const capacityRate = computed(() => {
  const s = data.value?.total_spots
  if (!s) return 0
  return Math.min(100, Math.round((data.value.registrations / s) * 100))
})

const capacityBarClass = computed(() => {
  const r = capacityRate.value
  return r >= 80 ? 'bg-emerald-500' : r >= 50 ? 'bg-amber-400' : 'bg-red-400'
})

const capacityRateTextClass = computed(() => {
  const r = capacityRate.value
  return r >= 80 ? 'text-emerald-600' : r >= 50 ? 'text-amber-600' : 'text-red-600'
})

// ── Sparkline ─────────────────────────────────────────────────────
const maxDailyCount = computed(() =>
  Math.max(...(data.value?.daily_registrations?.map(d => d.count) ?? [0]), 1)
)

function sparkBarPx(count) {
  if (!count) return 3
  return Math.max(6, Math.round((count / maxDailyCount.value) * 28))
}

function isToday(dateStr) {
  return dateStr === new Date().toISOString().slice(0, 10)
}

// ── Hilfs-computed für Stacked-Bar ────────────────────────────────
function shiftPct(n) {
  const total = data.value?.shifts
  return total ? (n / total) * 100 : 0
}

// ── Data loading ──────────────────────────────────────────────────
async function loadData() {
  loading.value = true
  data.value = null
  try {
    if (slug.value) {
      const res = await adminApi.getDashboard(slug.value)
      data.value = res.data.data
    } else if (auth.isAdmin) {
      const res = await adminApi.getGlobalDashboard()
      data.value = res.data.data
    }
  } catch { /* Instanz existiert evtl. nicht mehr */ }
  finally { loading.value = false }
}

onMounted(loadData)
watch(slug, loadData)

// ── EventBadge (inline component) ────────────────────────────────
const EventBadge = defineComponent({
  props: { type: String },
  setup(props) {
    return () => {
      const meta = EVENT_META[props.type] || { icon: null, label: props.type, color: 'bg-gray-100 text-gray-600' }
      return h('span', {
        class: `inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${meta.color}`,
      }, [
        meta.icon ? h(meta.icon, { class: 'w-3 h-3 flex-shrink-0' }) : null,
        h('span', meta.label),
      ])
    }
  },
})

// ── StatCard (inline component, used in both dashboards) ──────────
const StatCard = defineComponent({
  props: { label: String, value: [String, Number], sub: String, color: String, icon: Object },
  setup(props) {
    const iconColors = {
      blue:    'bg-blue-100 text-blue-600',
      emerald: 'bg-emerald-100 text-emerald-600',
      violet:  'bg-violet-100 text-violet-600',
      amber:   'bg-amber-100 text-amber-600',
      red:     'bg-red-100 text-red-600',
    }
    return () => h('div', { class: 'bg-white rounded-2xl p-4 lg:p-6 shadow-sm border border-gray-100' }, [
      h('div', { class: `w-9 h-9 lg:w-10 lg:h-10 rounded-xl flex items-center justify-center mb-2 lg:mb-3 ${iconColors[props.color] || iconColors.blue}` }, [
        props.icon ? h(props.icon, { class: 'w-4 h-4 lg:w-5 lg:h-5' }) : null,
      ]),
      h('p', { class: 'text-2xl lg:text-3xl font-bold text-gray-900 tabular-nums' }, String(props.value ?? '—')),
      h('p', { class: 'text-sm text-gray-500 mt-0.5' }, props.label),
      props.sub ? h('p', { class: 'text-xs text-gray-400 mt-1 leading-tight' }, props.sub) : null,
    ])
  },
})

// ── Fill-rate Helfer-Funktionen (Auslastung-Tabelle + Global-Dashboard) ──
function fillBarColor(rate) {
  return rate >= 90 ? 'bg-emerald-500' : rate >= 50 ? 'bg-amber-400' : 'bg-red-400'
}

function fillTextColor(rate) {
  return rate >= 90 ? 'text-emerald-700' : rate >= 50 ? 'text-amber-700' : 'text-red-600'
}

function fillBadgeColor(rate) {
  return rate >= 90 ? 'bg-emerald-100 text-emerald-700'
       : rate >= 50 ? 'bg-amber-100 text-amber-700'
       : 'bg-gray-100 text-gray-500'
}
</script>
