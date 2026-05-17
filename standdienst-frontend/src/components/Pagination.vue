<template>
  <div v-if="pages > 1" class="flex items-center justify-between py-3">
    <p class="text-sm text-gray-500">
      {{ (page - 1) * perPage + 1 }}–{{ Math.min(page * perPage, total) }} von {{ total }}
    </p>
    <div class="flex gap-1">
      <button
        v-for="p in pageRange"
        :key="p"
        class="w-8 h-8 text-sm rounded-lg flex items-center justify-center transition-colors"
        :class="p === page
          ? 'bg-primary-600 text-white'
          : p === '…' ? 'cursor-default text-gray-400' : 'text-gray-700 hover:bg-gray-100'"
        :disabled="p === '…'"
        @click="p !== '…' && $emit('update:page', p)"
      >{{ p }}</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  pages: { type: Number, required: true },
  total: { type: Number, required: true },
  perPage: { type: Number, default: 20 },
})
defineEmits(['update:page'])

const pageRange = computed(() => {
  const { page, pages } = props
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1)
  const range = []
  if (page <= 4) {
    range.push(1, 2, 3, 4, 5, '…', pages)
  } else if (page >= pages - 3) {
    range.push(1, '…', pages - 4, pages - 3, pages - 2, pages - 1, pages)
  } else {
    range.push(1, '…', page - 1, page, page + 1, '…', pages)
  }
  return range
})
</script>
