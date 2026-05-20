<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Instanz-Protokoll</h1>

    <!-- Kategorie-Filter -->
    <div class="mb-4 flex flex-wrap gap-2">
      <button
        v-for="cat in ACTIVITY_CATEGORIES"
        :key="cat.key"
        :class="[
          'px-3 py-1.5 rounded-full text-xs font-medium border transition-colors',
          activeCategory === cat.key
            ? 'bg-primary-600 text-white border-primary-600'
            : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400',
        ]"
        @click="setCategory(cat.key)"
      >{{ cat.label }}</button>
    </div>

    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="timestamp" @sort="toggleSort">Zeit</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="event_type" @sort="toggleSort">Ereignis</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="volunteer_name" @sort="toggleSort">Benutzer</SortTh>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Details</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3 text-gray-400 whitespace-nowrap text-xs">{{ fmtTime(log.timestamp) }}</td>
            <td class="px-4 py-3">
              <EventBadge :type="log.event_type" />
            </td>
            <td class="px-4 py-3 text-gray-600 text-xs">{{ log.volunteer_name || '—' }}</td>
            <td class="px-4 py-3 text-gray-500 text-xs max-w-xs truncate" :title="log.details">{{ log.details || '' }}</td>
          </tr>
          <tr v-if="!logs.length">
            <td colspan="4" class="px-4 py-8 text-center text-gray-400">Keine Einträge</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-model:page="page" :pages="pages" :total="total" :per-page="20" @update:page="load" />
  </div>
</template>

<script setup>
import { ref, onMounted, defineComponent, h } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import { EVENT_META, ACTIVITY_CATEGORIES, fmtTime } from '@/utils/activityLog'
import Pagination from '@/components/Pagination.vue'
import SortTh from '@/components/SortTh.vue'

const route = useRoute()
const logs = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const activeCategory = ref('')
const sortKey = ref('timestamp')
const sortDir = ref('desc')

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

onMounted(load)

function setCategory(key) {
  activeCategory.value = key
  page.value = 1
  load()
}

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
  page.value = 1
  load()
}

async function load() {
  const params = { page: page.value, per_page: 20, sort: sortKey.value, dir: sortDir.value }
  const cat = ACTIVITY_CATEGORIES.find(c => c.key === activeCategory.value)
  if (cat?.types.length) params.event_types = cat.types.join(',')
  const res = await adminApi.getInstanceActivity(route.params.slug, params)
  logs.value = res.data.data
  pages.value = res.data.pages
  total.value = res.data.total
}
</script>
