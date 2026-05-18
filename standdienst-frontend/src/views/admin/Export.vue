<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Export</h1>

    <div class="grid gap-4 max-w-2xl">
      <div class="card">
        <h2 class="text-base font-semibold text-gray-800 mb-4">Anmeldungen</h2>
        <div class="flex flex-wrap gap-3">
          <a :href="adminApi.exportUrl(slug, 'ods')" class="btn-secondary">
            <ArrowDownTrayIcon class="w-4 h-4" />
            ODS herunterladen
          </a>
          <a :href="adminApi.exportUrl(slug, 'pdf')" class="btn-secondary">
            <ArrowDownTrayIcon class="w-4 h-4" />
            PDF herunterladen
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDownTrayIcon } from '@heroicons/vue/24/outline'
import { adminApi } from '@/api/admin'

const route = useRoute()
const slug = computed(() => route.params.slug)
</script>
