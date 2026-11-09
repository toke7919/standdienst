<template>
  <div>
    <RouterView />
    <ToastContainer />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { RouterView, useRouter, useRoute } from 'vue-router'
import { setupApi } from '@/api/setup'
import { useSetupStore } from '@/stores/setup'
import { useAuthStore } from '@/stores/auth'
import { mayBypassMaintenance } from '@/utils/maintenance'
import ToastContainer from '@/components/ToastContainer.vue'

const router = useRouter()
const route = useRoute()
const setup = useSetupStore()
const auth = useAuthStore()

let _interval = null

function showMaintenance() {
  if (!route.meta?.maintenance) {
    router.push({ path: '/maintenance', query: { redirect: route.fullPath } })
  }
}

// API antwortet nicht (z. B. Neustart während eines Updates) → für alle die Wartungsseite
function onApiUnavailable() {
  setup.setMaintenance(true)
  showMaintenance()
}

onMounted(() => {
  window.addEventListener('api:unavailable', onApiUnavailable)
  _interval = setInterval(async () => {
    try {
      const res = await setupApi.status()
      const mode = res.data.data.maintenance_mode ?? false
      if (mode !== setup.maintenanceMode) {
        setup.setMaintenance(mode)
        // Rückkehr aus der Wartung übernimmt Maintenance.vue (inkl. Neuladen)
        if (mode && !mayBypassMaintenance(route.path, auth.isAdmin)) showMaintenance()
      }
    } catch { /* nicht erreichbar → behandelt der API-Client über „api:unavailable“ */ }
  }, 60_000)
})

onUnmounted(() => {
  window.removeEventListener('api:unavailable', onApiUnavailable)
  clearInterval(_interval)
})
</script>
