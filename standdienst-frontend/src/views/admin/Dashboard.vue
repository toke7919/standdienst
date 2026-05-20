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

      <!-- Letzte Aktivitäten (gefiltert auf Dienste + Essensspenden) -->
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
