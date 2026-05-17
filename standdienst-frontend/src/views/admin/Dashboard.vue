<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner size="lg" />
    </div>

    <div v-else-if="data" class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <StatCard label="Helfer" :value="data.volunteer_count" color="blue" />
      <StatCard label="Schichten" :value="data.shift_count" color="green" />
      <StatCard label="Anmeldungen" :value="data.registration_count" color="purple" />
      <StatCard label="Belegung" :value="`${data.fill_rate ?? 0}%`" color="orange" />
    </div>

    <div v-if="data?.recent_activity?.length" class="card">
      <h2 class="text-base font-semibold text-gray-800 mb-4">Letzte Aktivitäten</h2>
      <div class="space-y-2">
        <div
          v-for="log in data.recent_activity"
          :key="log.id"
          class="flex items-start gap-3 py-2 border-b border-gray-50 last:border-0"
        >
          <span class="text-xs text-gray-400 whitespace-nowrap mt-0.5 w-32 flex-shrink-0">
            {{ formatDate(log.created_at) }}
          </span>
          <span class="text-sm text-gray-700">{{ log.event_type }}</span>
          <span v-if="log.volunteer_name" class="text-sm text-gray-500 ml-auto">{{ log.volunteer_name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, defineComponent, h } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const auth = useAuthStore()
const route = useRoute()
const data = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const slug = route.params.slug || (auth.user?.instance_slug)
    if (slug) {
      const res = await adminApi.getDashboard(slug)
      data.value = res.data.data
    }
  } catch { /* ignore if no instance selected */ }
  finally {
    loading.value = false
  }
})

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })
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
