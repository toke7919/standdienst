<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">
      {{ slug ? `Dashboard – ${slug}` : 'Plattform-Dashboard' }}
    </h1>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner size="lg" />
    </div>

    <template v-else-if="data">
      <!-- Instanz-Dashboard -->
      <template v-if="slug">
        <!-- Zeile 1: Helfer / Schichten / Anmeldungen / Belegung -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <StatCard label="Helfer" :value="data.volunteers" color="blue" :icon="UsersIcon" />
          <StatCard label="Schichten gesamt" :value="data.shifts" color="violet" :icon="ClockIcon" />
          <StatCard label="Anmeldungen" :value="data.registrations" color="emerald" :icon="ClipboardDocumentListIcon" />
          <StatCard label="Belegung" :value="`${data.fill_rate ?? 0}%`" color="amber" :icon="SignalIcon" />
        </div>
        <!-- Zeile 2: Schicht-Belegung / freie Schichten / ohne Anmeldung / Helfer ohne Schicht -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            label="Schichten belegt"
            :value="data.shifts_full"
            :sub="`von ${data.shifts} gesamt`"
            color="emerald"
            :icon="CheckCircleIcon"
          />
          <StatCard
            label="Schichten frei"
            :value="data.shifts_free"
            color="blue"
            :icon="ClockIcon"
          />
          <StatCard
            label="Noch ohne Anmeldung"
            :value="data.shifts_empty"
            :sub="data.shifts_empty > 0 ? 'Schichten brauchen Helfer' : 'Alle Schichten besetzt'"
            color="amber"
            :icon="ExclamationCircleIcon"
          />
          <StatCard
            label="Helfer ohne Schicht"
            :value="data.volunteers_without_shift"
            color="violet"
            :icon="UserMinusIcon"
          />
        </div>

        <!-- Auslastung je Termin -->
        <div v-if="data.dates_fill?.length" class="card overflow-hidden !p-0 mb-8">
          <h2 class="text-base font-semibold text-gray-800 px-4 pt-4 pb-3">Auslastung je Termin</h2>
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-100 bg-gray-50">
                <th class="text-left px-4 py-2 font-medium text-gray-500">Datum</th>
                <th class="text-right px-4 py-2 font-medium text-gray-500">Schichten</th>
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
                    <div class="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        class="h-full rounded-full transition-all duration-300"
                        :class="fillBarColor(d.fill_rate)"
                        :style="`width: ${d.fill_rate}%`"
                      />
                    </div>
                    <span class="text-xs font-semibold w-9 text-right" :class="fillTextColor(d.fill_rate)">
                      {{ d.fill_rate }}%
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- Globales Admin-Dashboard -->
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
                  <th class="text-right py-2 px-3 font-medium text-gray-500">Schichten</th>
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

      <!-- Letzte Aktivitäten -->
      <div v-if="data.recent_activity?.length" class="card overflow-hidden p-0">
        <h2 class="text-base font-semibold text-gray-800 px-4 pt-4 pb-3">Letzte Aktivitäten</h2>
        <table class="w-full text-sm">
          <tbody>
            <tr v-for="log in data.recent_activity" :key="log.id"
                class="border-t border-gray-50 hover:bg-gray-50">
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
  UsersIcon, ClockIcon, ClipboardDocumentListIcon, SignalIcon,
  CheckCircleIcon, ShoppingBagIcon, ServerIcon,
  ExclamationCircleIcon, UserMinusIcon,
} from '@heroicons/vue/24/outline'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const data = ref(null)
const loading = ref(true)

const slug = computed(() => route.params.slug || null)

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
  finally {
    loading.value = false
  }
}

onMounted(loadData)
watch(slug, loadData)

const EventBadge = defineComponent({
  props: { type: String },
  setup(props) {
    return () => {
      const meta = EVENT_META[props.type] || { icon: null, label: props.type, color: 'bg-gray-100 text-gray-600' }
      return h('span', { class: `inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${meta.color}` }, [
        meta.icon ? h(meta.icon, { class: 'w-3 h-3 flex-shrink-0' }) : null,
        h('span', meta.label),
      ])
    }
  },
})

function fillBarColor(rate) {
  if (rate >= 90) return 'bg-green-500'
  if (rate >= 50) return 'bg-yellow-400'
  return 'bg-red-400'
}

function fillTextColor(rate) {
  if (rate >= 90) return 'text-green-700'
  if (rate >= 50) return 'text-yellow-700'
  return 'text-red-600'
}

function fillBadgeColor(rate) {
  if (rate >= 90) return 'bg-green-100 text-green-700'
  if (rate >= 50) return 'bg-yellow-100 text-yellow-700'
  return 'bg-gray-100 text-gray-600'
}

const StatCard = defineComponent({
  props: { label: String, value: [String, Number], sub: String, color: String, icon: Object },
  setup(props) {
    const iconColors = {
      blue:    'bg-blue-100 text-blue-600',
      emerald: 'bg-emerald-100 text-emerald-600',
      violet:  'bg-violet-100 text-violet-600',
      amber:   'bg-amber-100 text-amber-600',
    }
    return () => h('div', { class: 'bg-white rounded-xl p-5 shadow-sm border border-gray-100' }, [
      h('div', { class: `w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${iconColors[props.color] || iconColors.blue}` }, [
        props.icon ? h(props.icon, { class: 'w-5 h-5' }) : null,
      ]),
      h('p', { class: 'text-3xl font-bold text-gray-900 tabular-nums' }, String(props.value ?? '—')),
      h('p', { class: 'text-sm text-gray-500 mt-0.5' }, props.label),
      props.sub ? h('p', { class: 'text-xs text-gray-400 mt-1 leading-tight' }, props.sub) : null,
    ])
  },
})
</script>
