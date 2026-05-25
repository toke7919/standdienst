<template>
  <th
    class="px-4 py-3 text-left font-medium text-muted cursor-pointer select-none hover:text-ink/80 whitespace-nowrap"
    @click="$emit('sort', field)"
  >
    <slot />
    <span v-if="sortKey === field" class="ml-1 text-primary-500">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
    <span v-else class="ml-1 text-sand">↕</span>
  </th>
</template>

<script setup>
defineProps({ sortKey: String, sortDir: String, field: String })
defineEmits(['sort'])
</script>
