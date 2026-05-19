<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Instanz-Protokoll</h1>

    <!-- Filter-Chips -->
    <div class="mb-4 flex flex-wrap gap-2">
      <button
        v-for="(label, type) in { '': 'Alle', ...EVENT_LABELS }"
        :key="type"
        :class="[
          'px-3 py-1 rounded-full text-xs font-medium border transition-colors',
          filterType === type
            ? 'bg-primary-600 text-white border-primary-600'
            : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400',
        ]"
        @click="setFilter(type)"
      >
        {{ label }}
      </button>
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
            <td class="px-4 py-3 text-gray-400 whitespace-nowrap">{{ fmt(log.timestamp) }}</td>
            <td class="px-4 py-3">
              <span :class="['text-xs font-medium px-2 py-0.5 rounded-full', badgeClass(log.event_type)]">
                {{ EVENT_LABELS[log.event_type] || log.event_type }}
              </span>
            </td>
            <td class="px-4 py-3 text-gray-500">{{ log.volunteer_name || '—' }}</td>
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
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import Pagination from '@/components/Pagination.vue'
import SortTh from '@/components/SortTh.vue'

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

const route = useRoute()
const logs = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const filterType = ref('')
const sortKey = ref('timestamp')
const sortDir = ref('desc')

onMounted(load)

function setFilter(type) {
  filterType.value = type
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
  if (filterType.value) params.event_type = filterType.value
  const res = await adminApi.getInstanceActivity(route.params.slug, params)
  logs.value = res.data.data
  pages.value = res.data.pages
  total.value = res.data.total
}

function fmt(iso) {
  return iso ? new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }) : ''
}

function badgeClass(type) {
  return BADGE_CLASSES[type] || 'bg-gray-100 text-gray-600'
}
</script>
