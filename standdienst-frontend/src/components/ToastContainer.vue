<template>
  <div class="fixed right-4 z-50 flex flex-col gap-2 max-w-sm w-full bottom-[calc(4.5rem+env(safe-area-inset-bottom,0px))] md:bottom-4">
    <TransitionGroup name="toast">
      <div
        v-for="toast in ui.toasts"
        :key="toast.id"
        class="flex items-start gap-3 p-4 rounded-xl shadow-lg text-sm font-medium cursor-pointer select-none"
        :class="colorClass(toast.type)"
        @click="ui.removeToast(toast.id)"
      >
        <component :is="iconFor(toast.type)" class="w-5 h-5 flex-shrink-0 mt-0.5" />
        <span>{{ toast.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useUiStore } from '@/stores/ui'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/vue/24/outline'

const ui = useUiStore()

const colorClass = (type) => ({
  success: 'bg-green-50 text-green-800 border border-green-200',
  error: 'bg-red-50 text-red-800 border border-red-200',
  warning: 'bg-yellow-50 text-yellow-800 border border-yellow-200',
  info: 'bg-blue-50 text-blue-800 border border-blue-200',
}[type] || 'bg-bg-brand text-ink border border-sand')

const iconFor = (type) => ({
  success: CheckCircleIcon,
  error: ExclamationCircleIcon,
  warning: ExclamationTriangleIcon,
  info: InformationCircleIcon,
}[type] || InformationCircleIcon)
</script>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from { transform: translateX(100%); opacity: 0; }
.toast-leave-to { transform: translateX(100%); opacity: 0; }
</style>
