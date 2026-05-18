<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Globales Aktivitätsprotokoll</h1>

    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Zeit</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Ereignis</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Benutzer</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">IP</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3 text-gray-400 whitespace-nowrap">{{ fmt(log.timestamp) }}</td>
            <td class="px-4 py-3 font-medium">{{ log.event_type }}</td>
            <td class="px-4 py-3 text-gray-500">{{ log.volunteer_name || '—' }}</td>
            <td class="px-4 py-3 text-gray-400 font-mono text-xs">{{ log.ip_address || '—' }}</td>
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
import { adminApi } from '@/api/admin'
import Pagination from '@/components/Pagination.vue'

const logs = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)

onMounted(load)

async function load() {
  const res = await adminApi.getActivityLog({ page: page.value, per_page: 20 })
  logs.value = res.data.data
  pages.value = res.data.pages
  total.value = res.data.total
}

function fmt(iso) {
  return iso ? new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' }) : ''
}
</script>
