<template>
  <Modal v-model="show" :title="dialog?.title || 'Bestätigen'" size="sm">
    <p class="text-ink/80 mb-6">{{ dialog?.message }}</p>
    <div class="flex gap-3 justify-end">
      <button class="btn-secondary" @click="close(false)">
        {{ dialog?.cancelText || 'Abbrechen' }}
      </button>
      <button :class="dialog?.danger ? 'btn-danger' : 'btn-primary'" @click="close(true)">
        {{ dialog?.confirmText || 'Bestätigen' }}
      </button>
    </div>
  </Modal>
</template>

<script setup>
import { computed } from 'vue'
import { useUiStore } from '@/stores/ui'
import Modal from './Modal.vue'

const ui = useUiStore()
const dialog = computed(() => ui.confirmDialog)
const show = computed({
  get: () => !!dialog.value,
  set: (v) => { if (!v) ui.closeConfirm(false) },
})

function close(result) {
  ui.closeConfirm(result)
}
</script>
