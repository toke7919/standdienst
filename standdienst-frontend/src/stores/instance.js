import { defineStore } from 'pinia'
import { ref } from 'vue'
import { publicApi } from '@/api/public'

export const useInstanceStore = defineStore('instance', () => {
  const current = ref(null)
  const list = ref([])
  const loading = ref(false)

  async function loadInstance(slug) {
    loading.value = true
    try {
      const res = await publicApi.getInstanceInfo(slug)
      current.value = res.data.data
    } finally {
      loading.value = false
    }
  }

  async function loadList() {
    const res = await publicApi.getInstances()
    list.value = res.data.data
  }

  function clear() {
    current.value = null
  }

  return { current, list, loading, loadInstance, loadList, clear }
})
