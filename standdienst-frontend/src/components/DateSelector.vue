<template>
  <div class="space-y-1.5">
    <label class="flex items-center gap-3 cursor-pointer">
      <input
        type="checkbox"
        :checked="allSelected"
        :indeterminate.prop="someSelected && !allSelected"
        class="rounded-sm border-sand text-primary-600 focus:ring-primary-500"
        @change="toggleAll"
      />
      <span class="text-sm font-semibold text-ink">Alle auswählen</span>
    </label>
    <div class="border-t border-sand pt-2 space-y-1.5">
      <label v-for="d in dates" :key="d.id" class="flex items-center gap-2 cursor-pointer">
        <input
          :checked="modelValue.includes(d.id)"
          :value="d.id"
          type="checkbox"
          class="rounded-sm border-sand text-primary-600 focus:ring-primary-500"
          @change="toggle(d.id, $event)"
        />
        <span class="text-sm text-ink">{{ d.formatted }}</span>
        <span v-if="d.label" class="text-xs text-muted">{{ d.label }}</span>
        <span
          v-if="d.is_draft"
          class="inline-flex items-center px-1.5 py-0.5 rounded-sm text-[11px] font-medium bg-amber-100 text-amber-800"
        >Entwurf</span>
      </label>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Array, required: true },
  dates: { type: Array, required: true },
})
const emit = defineEmits(['update:modelValue'])

const allSelected = computed(() =>
  props.dates.length > 0 && props.modelValue.length === props.dates.length
)
const someSelected = computed(() => props.modelValue.length > 0)

function toggleAll(e) {
  emit('update:modelValue', e.target.checked ? props.dates.map(d => d.id) : [])
}

function toggle(id, e) {
  const next = e.target.checked
    ? [...props.modelValue, id]
    : props.modelValue.filter(x => x !== id)
  emit('update:modelValue', next)
}
</script>
