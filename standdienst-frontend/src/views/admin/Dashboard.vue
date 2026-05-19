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
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Helfer" :value="data.volunteers" color="blue" />
          <StatCard label="Schichten" :value="data.shifts" color="green" />
          <StatCard label="Anmeldungen" :value="data.registrations" color="purple" />
          <StatCard label="Belegung" :value="`${data.fill_rate ?? 0}%`" color="orange" />
        </div>
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Stände" :value="data.stands" color="blue" />
          <StatCard label="Termine" :value="data.dates" color="green" />
          <StatCard label="Voll belegt" :value="data.shifts_full" color="purple" />
          <StatCard label="Essensspenden" :value="data.food_donations" color="orange" />
        </div>
      </template>

      <!-- Globales Admin-Dashboard -->
      <template v-else>
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Instanzen" :value="data.instance_count" color="blue" />
          <StatCard label="Helfer gesamt" :value="data.total_volunteers" color="green" />
          <StatCard label="Anmeldungen" :value="data.total_registrations" color="purple" />
          <StatCard label="Essensspenden" :value="data.total_food_donations" color="orange" />
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
                  @click="$router.push(`/admin/${inst.slug}/volunteers`)"
                >
                  <td class="py-2 pr-4 font-medium text-gray-900">{{ inst.name }}</td>
                  <td class="py-2 px-3 text-right text-gray-600">{{ inst.volunteers }}</td>
                  <td class="py-2 px-3 text-right text-gray-600">{{ inst.shifts }}</td>
                  <td class="py-2 px-3 text-right text-gray-600">{{ inst.registrations }}</td>
                  <td class="py-2 px-3 text-right">
                    <span :class="fillColor(inst.fill_rate)" class="text-xs font-semibold px-2 py-0.5 rounded-full">
                      {{ inst.fill_rate }}%
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <!-- Letzte Aktivitäten (beide Ansichten) -->
      <div v-if="data.recent_activity?.length" class="card">
        <h2 class="text-base font-semibold text-gray-800 mb-4">Letzte Aktivitäten</h2>
        <div class="space-y-0">
          <div
            v-for="log in data.recent_activity"
            :key="log.id"
            class="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0"
          >
            <span class="text-xs text-gray-400 whitespace-nowrap w-28 flex-shrink-0">
              {{ fmt(log.timestamp) }}
            </span>
            <span :class="['text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0', badgeClass(log.event_type)]">
              {{ EVENT_LABELS[log.event_type] || log.event_type }}
            </span>
            <span v-if="log.volunteer_name" class="text-sm text-gray-500 truncate">
              {{ log.volunteer_name }}
            </span>
          </div>
        </div>
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
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const EVENT_LABELS = {
  shift_register: 'Schicht angemeldet',
  shift_unregister: 'Schicht abgemeldet',
  food_register: 'Essensspende',
  food_unregister: 'Essensspende storniert',
  login_success: 'Login erfolgreich',
  login_fail: 'Login fehlgeschlagen',
  volunteer_register: 'Registrierung',
  audit_settings: 'Einstellungen geändert',
  audit_data: 'Datenverwaltung',
  audit_organizer: 'Organizer verwaltet',
  audit_admin: 'Admin verwaltet',
}

const BADGE_CLASSES = {
  shift_register: 'bg-green-100 text-green-700',
  shift_unregister: 'bg-orange-100 text-orange-700',
  food_register: 'bg-teal-100 text-teal-700',
  food_unregister: 'bg-orange-100 text-orange-700',
  login_success: 'bg-blue-100 text-blue-700',
  login_fail: 'bg-red-100 text-red-700',
  volunteer_register: 'bg-purple-100 text-purple-700',
  audit_settings: 'bg-yellow-100 text-yellow-700',
  audit_data: 'bg-yellow-100 text-yellow-700',
  audit_organizer: 'bg-indigo-100 text-indigo-700',
  audit_admin: 'bg-indigo-100 text-indigo-700',
}

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

function fmt(iso) {
  return iso ? new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' }) : ''
}

function badgeClass(type) {
  return BADGE_CLASSES[type] || 'bg-gray-100 text-gray-600'
}

function fillColor(rate) {
  if (rate >= 90) return 'bg-green-100 text-green-700'
  if (rate >= 50) return 'bg-yellow-100 text-yellow-700'
  return 'bg-gray-100 text-gray-600'
}

const StatCard = defineComponent({
  props: { label: String, value: [String, Number], color: String },
  setup(props) {
    const colors = {
      blue: 'bg-blue-50 text-blue-700',
      green: 'bg-green-50 text-green-700',
      purple: 'bg-purple-50 text-purple-700',
      orange: 'bg-orange-50 text-orange-700',
    }
    return () => h('div', { class: `rounded-xl p-5 ${colors[props.color] || colors.blue}` }, [
      h('p', { class: 'text-sm font-medium opacity-70' }, props.label),
      h('p', { class: 'text-3xl font-bold mt-1' }, String(props.value ?? '—')),
    ])
  },
})
</script>
