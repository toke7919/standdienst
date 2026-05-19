<template>
  <th
    class="px-4 py-3 text-left font-medium text-gray-500 cursor-pointer select-none hover:text-gray-700 whitespace-nowrap"
    @click="$emit('sort', field)"
  >
    <slot />
    <span v-if="sortKey === field" class="ml-1 text-primary-500">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
    <span v-else class="ml-1 text-gray-300">↕</span>
  </th>
</template>

<script setup>
defineProps({ sortKey: String, sortDir: String, field: String })
defineEmits(['sort'])
</script>
