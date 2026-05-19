import { defineStore } from 'pinia'
import { ref } from 'vue'
import { publicApi } from '@/api/public'
import { applyTheme, resetTheme } from '@/utils/colorPalette'

export const useInstanceStore = defineStore('instance', () => {
  const current = ref(null)
  const currentSlug = ref(null)
  const list = ref([])
  const loading = ref(false)

  async function loadInstance(slug) {
    if (slug === currentSlug.value && current.value) return
    loading.value = true
    currentSlug.value = slug
    try {
      const res = await publicApi.getInstanceInfo(slug)
      current.value = res.data.data
      if (res.data.data?.primary_color) {
        applyTheme(res.data.data.primary_color)
      }
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
    currentSlug.value = null
    resetTheme()
  }

  function invalidateCache() {
    currentSlug.value = null
  }

  return { current, currentSlug, list, loading, loadInstance, loadList, clear, invalidateCache }
})
