import { ref, computed } from 'vue'

export function useSort(items, defaultKey = null, defaultDir = 'asc') {
  const sortKey = ref(defaultKey)
  const sortDir = ref(defaultDir)

  const sorted = computed(() => {
    if (!sortKey.value) return items.value
    return [...items.value].sort((a, b) => {
      const va = a[sortKey.value] ?? ''
      const vb = b[sortKey.value] ?? ''
      const cmp = String(va).localeCompare(String(vb), 'de', { numeric: true })
      return sortDir.value === 'asc' ? cmp : -cmp
    })
  })

  function toggleSort(key) {
    if (sortKey.value === key) {
      sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortKey.value = key
      sortDir.value = 'asc'
    }
  }

  return { sortKey, sortDir, sorted, toggleSort }
}
