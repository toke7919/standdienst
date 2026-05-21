import { defineStore } from 'pinia'
import { ref } from 'vue'
import { publicApi } from '@/api/public'
import { applyTheme, resetTheme } from '@/utils/colorPalette'

export const useInstanceStore = defineStore('instance', () => {
  const current = ref(null)
  const currentSlug = ref(null)
  const list = ref([])
  const loading = ref(false)
  const notFound = ref(false)
  const globalInfo = ref(null)

  async function loadInstance(slug) {
    if (slug === currentSlug.value && current.value) return
    loading.value = true
    notFound.value = false
    currentSlug.value = slug
    try {
      const res = await publicApi.getInstanceInfo(slug)
      if (slug !== currentSlug.value) return
      current.value = res.data.data
      if (res.data.data?.primary_color) {
        applyTheme(res.data.data.primary_color)
      }
    } catch (e) {
      if (e.response?.status === 404) notFound.value = true
    } finally {
      loading.value = false
    }
  }

  async function loadList() {
    const res = await publicApi.getInstances()
    list.value = res.data.data
  }

  async function loadGlobalInfo() {
    if (globalInfo.value) return
    try {
      const res = await publicApi.getPlatformInfo()
      globalInfo.value = res.data.data
    } catch { /* ignore */ }
  }

  function clear() {
    current.value = null
    currentSlug.value = null
    notFound.value = false
    resetTheme()
  }

  function invalidateCache() {
    currentSlug.value = null
  }

  return { current, currentSlug, list, loading, notFound, globalInfo, loadInstance, loadList, loadGlobalInfo, clear, invalidateCache }
})
