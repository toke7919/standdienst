<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-ink">
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
            <p class="self-start text-xs font-semibold text-muted uppercase tracking-wider mb-3 lg:mb-5">Dienstbelegung</p>

            <!-- SVG Donut -->
            <div class="relative w-28 h-28 lg:w-36 lg:h-36 mb-3 lg:mb-5">
              <svg viewBox="0 0 100 100" class="w-full h-full">
                <circle cx="50" cy="50" r="36" fill="none" stroke="var(--color-sand, #e5e0d8)" stroke-width="11" />
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
                <span class="text-[11px] text-muted mt-0.5 font-medium">Belegung</span>
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
                <span class="text-muted flex-1">Vollbesetzt</span>
                <span class="font-bold tabular-nums text-ink/80">{{ data.shifts_full }}</span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <div class="w-2.5 h-2.5 rounded-full bg-amber-400 flex-shrink-0" />
                <span class="text-muted flex-1">Teilbesetzt</span>
                <span class="font-bold tabular-nums text-ink/80">{{ data.shifts_free - data.shifts_empty }}</span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <div class="w-2.5 h-2.5 rounded-full bg-red-300 flex-shrink-0" />
                <span class="text-muted flex-1">Leer</span>
                <span class="font-bold tabular-nums" :class="data.shifts_empty > 0 ? 'text-red-500' : 'text-muted'">
                  {{ data.shifts_empty }}
                </span>
              </div>
            </div>
          </div>

          <!-- Nächster Termin -->
          <div class="card flex flex-col">
            <p class="text-xs font-semibold text-muted uppercase tracking-wider mb-3">Nächster Termin</p>

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
                  <span class="text-xl font-semibold text-sand mb-2 leading-none">
                    {{ data.next_event.days_until === 1 ? 'Tag' : 'Tage' }}
                  </span>
                </div>
              </template>

              <p class="text-sm font-medium text-ink/80 text-center leading-snug">
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

            <div v-else class="flex-1 flex flex-col items-center justify-center text-sand py-4">
              <CalendarDaysIcon class="w-16 h-16 mb-3" />
              <p class="text-sm text-muted">Keine anstehenden Termine</p>
            </div>
          </div>

          <!-- Gesamtkapazität -->
          <div class="card flex flex-col">
            <p class="text-xs font-semibold text-muted uppercase tracking-wider mb-3">Gesamtkapazität</p>

            <div class="flex items-end gap-1.5 mb-3 lg:mb-5">
              <span class="text-4xl lg:text-5xl font-black tabular-nums leading-none text-ink">{{ data.registrations }}</span>
              <span class="text-xl text-sand mb-1">/</span>
              <span class="text-xl font-semibold text-muted mb-1">{{ data.total_spots }}</span>
              <span class="text-sm text-muted mb-1.5">Plätze</span>
            </div>

            <!-- Gradient progress bar -->
            <div class="h-3 bg-bg-brand rounded-full overflow-hidden mb-1.5">
              <div
                class="h-full rounded-full transition-all duration-700"
                :class="capacityBarClass"
                :style="`width:${capacityRate}%`"
              />
            </div>
            <div class="flex justify-between items-center mb-5">
              <span class="text-xs text-muted">{{ data.registrations }} belegt</span>
              <span class="text-sm font-bold tabular-nums" :class="capacityRateTextClass">{{ capacityRate }}%</span>
            </div>

            <!-- Freie Plätze sub-stat -->
            <div class="mt-auto pt-4 border-t border-sand flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                <ClockIcon class="w-4 h-4 text-blue-500" />
              </div>
              <div>
                <p class="text-lg font-black tabular-nums text-ink leading-none">
                  {{ Math.max(0, (data.total_spots || 0) - data.registrations) }}
                </p>
                <p class="text-xs text-muted">freie Plätze</p>
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
                <p class="text-2xl font-black tabular-nums text-ink">{{ data.volunteers }}</p>
                <p class="text-sm text-muted mt-0.5">Helfer</p>
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
                <p class="text-2xl font-black tabular-nums text-ink">{{ data.registrations }}</p>
                <p class="text-sm text-muted mt-0.5">Anmeldungen</p>
              </div>
              <div class="w-9 h-9 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
                <ClipboardDocumentListIcon class="w-5 h-5 text-primary-600" />
              </div>
            </div>
            <div v-if="data.daily_registrations?.length" class="flex items-end gap-px h-8">
              <div
                v-for="d in data.daily_registrations"
                :key="d.date"
                class="flex-1 rounded-t-[2px] transition-all duration-500"
                :class="isToday(d.date) ? 'bg-primary-500' : 'bg-primary-200'"
                :style="`height:${sparkBarPx(d.count)}px`"
              />
            </div>
            <p class="text-xs text-muted mt-1">7-Tage-Trend</p>
          </div>

          <!-- Leere Dienste – Alert-Karte -->
          <div
            :class="['rounded-md shadow-sm border p-4 lg:p-6 transition-colors duration-300',
                     data.shifts_empty > 0 ? 'bg-red-50 border-red-200' : 'bg-soft border-sand']"
          >
            <div class="flex items-start justify-between mb-3">
              <div>
                <p
                  class="text-2xl font-black tabular-nums"
                  :class="data.shifts_empty > 0 ? 'text-red-600' : 'text-ink'"
                >{{ data.shifts_empty }}</p>
                <p class="text-sm text-muted mt-0.5">Dienste leer</p>
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
          <h2 class="text-base font-semibold text-ink px-4 pt-4 pb-3">Auslastung je Termin</h2>
          <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-sand bg-bg-brand">
                <th class="text-left px-4 py-2 font-medium text-muted">Datum</th>
                <th class="text-right px-4 py-2 font-medium text-muted">Dienste</th>
                <th class="text-right px-4 py-2 font-medium text-muted">Vollbelegt</th>
                <th class="text-right px-4 py-2 font-medium text-muted pr-5">Belegung</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="d in data.dates_fill"
                :key="d.date_id"
                class="border-b border-sand last:border-0 hover:bg-bg-warm"
              >
                <td class="px-4 py-2.5 font-medium text-ink">{{ d.date_formatted }}</td>
                <td class="px-4 py-2.5 text-right text-ink/80">{{ d.shifts }}</td>
                <td class="px-4 py-2.5 text-right text-ink/80">{{ d.shifts_full }}</td>
                <td class="px-4 py-2.5 text-right pr-5">
                  <div class="inline-flex items-center gap-2">
                    <div class="w-20 h-2 bg-bg-brand rounded-full overflow-hidden">
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

        <!-- ── ROW 1: Hero KPIs ─────────────────────────────────────── -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">

          <!-- Plattform-Belegungsring -->
          <div class="card flex flex-col items-center">
            <p class="self-start text-xs font-semibold text-muted uppercase tracking-wider mb-3">Plattform-Belegung</p>
            <div class="relative w-28 h-28 lg:w-36 lg:h-36 mb-3">
              <svg viewBox="0 0 100 100" class="w-full h-full">
                <circle cx="50" cy="50" r="36" fill="none" stroke="var(--color-sand, #e5e0d8)" stroke-width="11" />
                <circle
                  cx="50" cy="50" r="36"
                  fill="none"
                  :stroke="globalRingColor"
                  stroke-width="11"
                  stroke-linecap="round"
                  :stroke-dasharray="`${globalRingDash.toFixed(1)} ${RING_C.toFixed(1)}`"
                  transform="rotate(-90 50 50)"
                  style="transition: stroke-dasharray 0.9s cubic-bezier(0.34,1.56,0.64,1)"
                />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-2xl font-black tabular-nums leading-none" :style="`color:${globalRingColor}`">
                  {{ data.overall_fill_rate }}%
                </span>
                <span class="text-[11px] text-muted mt-0.5 font-medium">Belegung</span>
              </div>
            </div>
            <div class="w-full space-y-1.5 text-xs">
              <div class="flex justify-between">
                <span class="text-muted">Vollbesetzte Dienste</span>
                <span class="font-bold tabular-nums text-ink/80">{{ data.total_shifts_full }} / {{ data.total_shifts }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted">Belegte Plätze</span>
                <span class="font-bold tabular-nums text-ink/80">{{ data.total_registrations }} / {{ data.total_spots }}</span>
              </div>
            </div>
          </div>

          <!-- Anmeldungen + 7-Tage-Sparkline -->
          <div class="card flex flex-col">
            <p class="text-xs font-semibold text-muted uppercase tracking-wider mb-3">Anmeldungen (7 Tage)</p>
            <div class="flex items-end gap-1 h-16 mb-2">
              <div
                v-for="d in data.daily_registrations"
                :key="d.date"
                class="flex-1 flex flex-col items-center gap-0.5"
              >
                <div
                  class="w-full rounded-t-[2px] transition-all duration-500"
                  :class="isToday(d.date) ? 'bg-primary-500' : 'bg-primary-200'"
                  :style="`height:${globalSparkPx(d.count)}px`"
                />
              </div>
            </div>
            <div class="flex justify-between mb-4">
              <span
                v-for="d in data.daily_registrations"
                :key="d.date"
                class="flex-1 text-center text-[10px]"
                :class="isToday(d.date) ? 'text-primary-600 font-semibold' : 'text-muted'"
              >{{ d.day_short }}</span>
            </div>
            <div class="mt-auto pt-3 border-t border-sand flex items-center justify-between">
              <span class="text-xs text-muted">Gesamt</span>
              <span class="text-2xl font-black tabular-nums text-ink">{{ data.total_registrations }}</span>
            </div>
          </div>

          <!-- Plattform-Zählkacheln -->
          <div class="grid grid-cols-2 gap-3 sm:col-span-2 lg:col-span-1">
            <StatCard label="Instanzen" :value="data.instance_count" color="blue" :icon="ServerIcon" />
            <StatCard label="Helfer" :value="data.total_volunteers" color="emerald" :icon="UsersIcon" />
            <StatCard label="Dienste" :value="data.total_shifts" color="violet" :icon="ClipboardDocumentListIcon" />
            <StatCard label="Essensspenden" :value="data.total_food_donations" color="amber" :icon="ShoppingBagIcon" />
          </div>
        </div>

        <!-- ── Instanzübersicht ─────────────────────────────────────── -->
        <div v-if="data.instances?.length" class="card overflow-hidden !p-0 mb-8">
          <h2 class="text-base font-semibold text-ink px-4 pt-4 pb-3">Instanzübersicht</h2>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-sand bg-bg-brand">
                  <th class="text-left px-4 py-2 font-medium text-muted">Instanz</th>
                  <th class="text-right px-4 py-2 font-medium text-muted">Helfer</th>
                  <th class="text-right px-4 py-2 font-medium text-muted">Dienste</th>
                  <th class="text-right px-4 py-2 font-medium text-muted">Anmeldungen</th>
                  <th class="text-right px-4 py-2 font-medium text-muted pr-5">Belegung</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="inst in data.instances"
                  :key="inst.id"
                  class="border-b border-sand last:border-0 hover:bg-bg-warm cursor-pointer"
                  @click="$router.push(`/admin/${inst.slug}/dashboard`)"
                >
                  <td class="px-4 py-2.5 font-medium text-ink">{{ inst.name }}</td>
                  <td class="px-4 py-2.5 text-right text-ink/80">{{ inst.volunteers }}</td>
                  <td class="px-4 py-2.5 text-right text-ink/80">{{ inst.shifts }}</td>
                  <td class="px-4 py-2.5 text-right text-ink/80">{{ inst.registrations }}</td>
                  <td class="px-4 py-2.5 text-right pr-5">
                    <div class="inline-flex items-center gap-2">
                      <div class="w-16 h-2 bg-bg-brand rounded-full overflow-hidden">
                        <div
                          class="h-full rounded-full"
                          :class="fillBarColor(inst.fill_rate)"
                          :style="`width:${inst.fill_rate}%`"
                        />
                      </div>
                      <span class="text-xs font-semibold w-9 text-right tabular-nums" :class="fillTextColor(inst.fill_rate)">
                        {{ inst.fill_rate }}%
                      </span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <!-- ── Letzte Aktivitäten (beide Dashboards) ──────────────────── -->
      <div v-if="data.recent_activity?.length" class="card overflow-hidden !p-0">
        <h2 class="text-base font-semibold text-ink px-4 pt-4 pb-3">Letzte Aktivitäten</h2>

        <!-- Mobile: gestapelte Liste (kein horizontales Overflow) -->
        <div class="md:hidden divide-y divide-sand">
          <div
            v-for="log in data.recent_activity"
            :key="log.id"
            class="flex items-start gap-3 px-4 py-3"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-0.5 flex-wrap">
                <EventBadge :type="log.event_type" />
                <span class="text-xs text-ink/80 truncate">{{ log.volunteer_name || '—' }}</span>
              </div>
              <p v-if="log.details" class="text-xs text-muted truncate">{{ log.details }}</p>
            </div>
            <span class="text-xs text-sand flex-shrink-0 mt-0.5">{{ fmtTime(log.timestamp) }}</span>
          </div>
        </div>

        <!-- Desktop: Tabelle -->
        <table class="hidden md:table w-full text-sm">
          <tbody>
            <tr
              v-for="log in data.recent_activity"
              :key="log.id"
              class="border-t border-sand hover:bg-bg-warm"
            >
              <td class="px-4 py-2.5 text-muted whitespace-nowrap text-xs w-32 flex-shrink-0">
                {{ fmtTime(log.timestamp) }}
              </td>
              <td class="px-4 py-2.5">
                <EventBadge :type="log.event_type" />
              </td>
              <td class="px-4 py-2.5 text-ink/80 text-xs">{{ log.volunteer_name || '—' }}</td>
              <td class="px-4 py-2.5 text-muted text-xs max-w-xs truncate" :title="log.details">
                {{ log.details || '' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div v-else class="text-center text-muted py-16">
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

// ── SVG Donut (Instanz + Global) ───────────────────────────────────
const RING_R = 36
const RING_C = 2 * Math.PI * RING_R          // ≈ 226.2
const ringDashAnimated = ref(0)
const globalRingDash = ref(0)

watch(data, (newVal) => {
  if (!newVal) { ringDashAnimated.value = 0; globalRingDash.value = 0; return }
  ringDashAnimated.value = 0
  globalRingDash.value = 0
  requestAnimationFrame(() => requestAnimationFrame(() => {
    ringDashAnimated.value = ((newVal.fill_rate ?? 0) / 100) * RING_C
    globalRingDash.value = ((newVal.overall_fill_rate ?? 0) / 100) * RING_C
  }))
}, { immediate: true })

const ringColor = computed(() => {
  const r = data.value?.fill_rate ?? 0
  return r >= 80 ? '#10b981' : r >= 50 ? '#f59e0b' : '#ef4444'
})

const globalRingColor = computed(() => {
  const r = data.value?.overall_fill_rate ?? 0
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

function globalSparkPx(count) {
  if (!count) return 3
  return Math.max(6, Math.round((count / maxDailyCount.value) * 52))
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
      const meta = EVENT_META[props.type] || { icon: null, label: props.type, color: 'bg-bg-brand text-ink/80' }
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
      violet:  'bg-primary-100 text-primary-600',
      amber:   'bg-amber-100 text-amber-600',
      red:     'bg-red-100 text-red-600',
    }
    return () => h('div', { class: 'bg-soft rounded-md p-4 lg:p-6 shadow-sm border border-sand' }, [
      h('div', { class: `w-9 h-9 lg:w-10 lg:h-10 rounded-xl flex items-center justify-center mb-2 lg:mb-3 ${iconColors[props.color] || iconColors.blue}` }, [
        props.icon ? h(props.icon, { class: 'w-4 h-4 lg:w-5 lg:h-5' }) : null,
      ]),
      h('p', { class: 'text-2xl lg:text-3xl font-bold text-ink tabular-nums' }, String(props.value ?? '—')),
      h('p', { class: 'text-sm text-muted mt-0.5' }, props.label),
      props.sub ? h('p', { class: 'text-xs text-muted mt-1 leading-tight' }, props.sub) : null,
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
       : 'bg-bg-brand text-muted'
}
</script>
