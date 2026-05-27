import { ref } from 'vue'
import { defineStore } from 'pinia'
import { setupApi } from '@/api/setup'

export const useSetupStore = defineStore('setup', () => {
  const complete = ref(null) // null=unbekannt, true/false=geprüft
  const maintenanceMode = ref(false)

  async function check() {
    if (complete.value !== null) return complete.value
    try {
      const res = await setupApi.status()
      complete.value = res.data.data.setup_complete
      maintenanceMode.value = res.data.data.maintenance_mode ?? false
    } catch {
      complete.value = true // Im Fehlerfall nicht blockieren
    }
    return complete.value
  }

  function markComplete() {
    complete.value = true
  }

  function setMaintenance(mode) {
    maintenanceMode.value = mode
  }

  return { complete, maintenanceMode, check, markComplete, setMaintenance }
})
