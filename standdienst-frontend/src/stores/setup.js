import { ref } from 'vue'
import { defineStore } from 'pinia'
import { setupApi } from '@/api/setup'

export const useSetupStore = defineStore('setup', () => {
  const complete = ref(null) // null=unbekannt, true/false=geprüft

  async function check() {
    if (complete.value !== null) return complete.value
    try {
      const res = await setupApi.status()
      complete.value = res.data.data.setup_complete
    } catch {
      complete.value = true // Im Fehlerfall nicht blockieren
    }
    return complete.value
  }

  function markComplete() {
    complete.value = true
  }

  return { complete, check, markComplete }
})
