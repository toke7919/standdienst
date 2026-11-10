<!--
  Zeilen-Aktion (Bearbeiten/Duplizieren/Löschen) in Listen:
  unterhalb von sm nur Icon (mit aria-label, große Tippfläche), ab sm Text.
  Schriftgröße bestimmt der Aufrufer per class (z. B. text-xs / text-sm).
-->
<template>
  <button
    type="button"
    :aria-label="text"
    :title="title || undefined"
    :disabled="disabled"
    class="inline-flex items-center justify-center p-2 -m-1 sm:p-0 sm:m-0 rounded-md font-medium disabled:cursor-not-allowed"
    :class="disabled ? 'text-sand' : COLORS[action]"
    @click="!disabled && emit('click', $event)"
  >
    <component :is="ICONS[action]" class="w-5 h-5 sm:hidden" aria-hidden="true" />
    <span class="hidden sm:inline">{{ text }}</span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { PencilSquareIcon, DocumentDuplicateIcon, TrashIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  action: {
    type: String,
    required: true,
    validator: v => ['edit', 'duplicate', 'delete'].includes(v),
  },
  label: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  title: { type: String, default: '' },
})

const emit = defineEmits(['click'])

const ICONS = { edit: PencilSquareIcon, duplicate: DocumentDuplicateIcon, delete: TrashIcon }
const LABELS = { edit: 'Bearbeiten', duplicate: 'Duplizieren', delete: 'Löschen' }
const COLORS = {
  edit: 'text-primary-600 hover:text-primary-800',
  duplicate: 'text-muted hover:text-ink',
  delete: 'text-red-500 hover:text-red-700',
}

const text = computed(() => props.label || LABELS[props.action])
</script>
