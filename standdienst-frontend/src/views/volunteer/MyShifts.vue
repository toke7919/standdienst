<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-bold text-gray-900">Meine Schichten</h1>
      <a :href="icsUrl" class="btn-secondary text-sm">
        <CalendarIcon class="w-4 h-4" />
        Als iCal herunterladen
      </a>
    </div>

    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <div v-else class="space-y-3">
      <div
        v-for="reg in registrations"
        :key="reg.id"
        class="card flex items-center justify-between p-4"
      >
        <div>
          <p class="font-medium text-gray-900">{{ reg.stand_name }}</p>
          <p class="text-sm text-gray-500">{{ reg.date_formatted }} · {{ reg.time_range }}</p>
        </div>
        <button class="text-sm text-red-600 hover:underline" @click="cancel(reg)">Abmelden</button>
      </div>
      <p v-if="!registrations.length" class="text-center text-gray-400 py-12">
        Noch keine Anmeldungen
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { CalendarIcon } from '@heroicons/vue/24/outline'
import { volunteerApi } from '@/api/volunteer'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const registrations = ref([])
const loading = ref(true)

const icsUrl = computed(() => `/api/volunteer/${route.params.slug}/my-registrations/ical`)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await volunteerApi.getMyRegistrations(route.params.slug)
    registrations.value = res.data.data
  } finally {
    loading.value = false
  }
}

async function cancel(reg) {
  const ok = await ui.confirm({
    title: 'Abmelden', message: `Von der Schicht ${reg.stand_name} abmelden?`, confirmText: 'Abmelden', danger: true,
  })
  if (!ok) return
  try {
    await volunteerApi.unregisterShift(route.params.slug, reg.shift_id)
    ui.success('Abgemeldet')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
