<template>
  <div>
    <h1 class="text-2xl font-bold text-ink mb-6">Globales Aktivitätsprotokoll</h1>

    <!-- Filter-Leiste -->
    <div class="mb-3 flex flex-wrap gap-2 items-center">
      <!-- Instanz-Filter -->
      <select v-model="selectedInstanceId" class="input text-xs py-1.5 max-w-[14rem]" @change="onFilterChange">
        <option :value="null">Alle Instanzen</option>
        <option v-for="inst in instances" :key="inst.id" :value="inst.id">{{ inst.name }}</option>
      </select>

      <!-- Kategorie-Filter -->
      <button
        v-for="cat in ACTIVITY_CATEGORIES"
        :key="cat.key"
        :class="[
          'px-3 py-1.5 rounded-full text-xs font-medium border transition-colors',
          activeCategory === cat.key
            ? 'bg-primary-600 text-white border-primary-600'
            : 'bg-soft text-ink/80 border-sand hover:border-ink/80',
        ]"
        @click="setCategory(cat.key)"
      >{{ cat.label }}</button>
    </div>

    <div class="card overflow-hidden p-0">
      <!-- Mobile: gestapelte Liste -->
      <div class="md:hidden divide-y divide-sand">
        <div
          v-for="log in logs"
          :key="log.id"
          class="flex items-start gap-3 px-4 py-3"
        >
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-0.5 flex-wrap">
              <EventBadge :type="log.event_type" />
              <span class="text-xs text-ink/80 truncate">{{ log.volunteer_name || '—' }}</span>
            </div>
            <div class="mt-0.5">
              <RouterLink
                v-if="log.instance_slug"
                :to="`/admin/${log.instance_slug}/dashboard`"
                class="text-xs text-primary-600 hover:underline"
              >{{ log.instance_name }}</RouterLink>
              <span v-else class="text-xs text-muted">Plattform</span>
            </div>
            <p v-if="log.details" class="text-xs text-muted truncate mt-0.5">{{ log.details }}</p>
          </div>
          <span class="text-xs text-sand flex-shrink-0 mt-0.5">{{ fmtTime(log.timestamp) }}</span>
        </div>
        <div v-if="!logs.length" class="px-4 py-8 text-center text-muted text-sm">Keine Einträge</div>
      </div>

      <!-- Desktop: Tabelle -->
      <table class="hidden md:table w-full text-sm">
        <thead class="bg-bg-brand border-b border-sand">
          <tr>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="timestamp" @sort="toggleSort">Zeit</SortTh>
            <th class="px-4 py-3 text-left font-medium text-muted">Instanz</th>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="event_type" @sort="toggleSort">Ereignis</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="volunteer_name" @sort="toggleSort">Benutzer</SortTh>
            <th class="px-4 py-3 text-left font-medium text-muted">IP</th>
            <th class="px-4 py-3 text-left font-medium text-muted">Details</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id" class="border-b border-sand hover:bg-bg-warm">
            <td class="px-4 py-3 text-muted whitespace-nowrap text-xs">{{ fmtTime(log.timestamp) }}</td>
            <td class="px-4 py-3 text-xs">
              <RouterLink
                v-if="log.instance_slug"
                :to="`/admin/${log.instance_slug}/dashboard`"
                class="text-primary-600 hover:underline"
              >{{ log.instance_name }}</RouterLink>
              <span v-else class="text-muted">Plattform</span>
            </td>
            <td class="px-4 py-3">
              <EventBadge :type="log.event_type" />
            </td>
            <td class="px-4 py-3 text-ink/80 text-xs">{{ log.volunteer_name || '—' }}</td>
            <td class="px-4 py-3 text-muted font-mono text-xs">{{ log.ip_address || '—' }}</td>
            <td class="px-4 py-3 text-muted text-xs max-w-xs truncate" :title="log.details">{{ log.details || '' }}</td>
          </tr>
          <tr v-if="!logs.length">
            <td colspan="6" class="px-4 py-8 text-center text-muted">Keine Einträge</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-model:page="page" :pages="pages" :total="total" :per-page="20" @update:page="load" />
  </div>
</template>

<script setup>
import { ref, onMounted, defineComponent, h } from 'vue'
import { RouterLink } from 'vue-router'
import { adminApi } from '@/api/admin'
import { EVENT_META, ACTIVITY_CATEGORIES, fmtTime } from '@/utils/activityLog'
import Pagination from '@/components/Pagination.vue'
import SortTh from '@/components/SortTh.vue'

const logs = ref([])
const instances = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const activeCategory = ref('')
const selectedInstanceId = ref(null)
const sortKey = ref('timestamp')
const sortDir = ref('desc')

const EventBadge = defineComponent({
  props: { type: String },
  setup(props) {
    return () => {
      const meta = EVENT_META[props.type] || { icon: null, label: props.type, color: 'bg-bg-brand text-ink/80' }
      return h('span', { class: `inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${meta.color}` }, [
        meta.icon ? h(meta.icon, { class: 'w-3 h-3 flex-shrink-0' }) : null,
        h('span', meta.label),
      ])
    }
  },
})

onMounted(async () => {
  try {
    const res = await adminApi.getInstances({ per_page: 200 })
    instances.value = res.data.data
  } catch { /* ignore */ }
  await load()
})

function setCategory(key) {
  activeCategory.value = key
  page.value = 1
  load()
}

function onFilterChange() {
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
  if (selectedInstanceId.value !== null) params.instance_id = selectedInstanceId.value
  const cat = ACTIVITY_CATEGORIES.find(c => c.key === activeCategory.value)
  if (cat?.types.length) params.event_types = cat.types.join(',')
  const res = await adminApi.getActivityLog(params)
  logs.value = res.data.data
  pages.value = res.data.pages
  total.value = res.data.total
}
</script>
