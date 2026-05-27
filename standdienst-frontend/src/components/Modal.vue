<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40" @click="!persistent && $emit('update:modelValue', false)" />
        <div
          class="relative bg-soft rounded-md border border-sand shadow-lg w-full max-h-[90vh] overflow-y-auto overflow-x-hidden"
          :class="sizeClass"
        >
          <div v-if="title" class="flex items-center justify-between p-6 border-b border-sand">
            <h2 class="text-lg font-semibold text-ink">{{ title }}</h2>
            <button
              v-if="!persistent"
              class="p-1 rounded-lg text-muted hover:text-ink/80 hover:bg-bg-warm transition-colors"
              @click="$emit('update:modelValue', false)"
            >
              <XMarkIcon class="w-5 h-5" />
            </button>
          </div>
          <div class="p-6">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  modelValue: Boolean,
  title: String,
  size: { type: String, default: 'md' },
  persistent: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])

const sizeClass = computed(() => ({
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
}[props.size]))
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: all 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .relative, .modal-leave-to .relative { transform: scale(0.95); }
</style>
