<template>
  <div class="flex items-center justify-center" :class="wrapClass">
    <div
      class="animate-spin rounded-full border-2 border-current border-t-transparent"
      :class="sizeClass"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  size: { type: String, default: 'md' },
  fullPage: Boolean,
})
const sizeClass = computed(() => ({ sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' }[props.size]))
const wrapClass = computed(() => props.fullPage ? 'min-h-screen text-primary-600' : 'py-8 text-gray-400')
</script>
