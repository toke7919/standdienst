import { defineStore } from 'pinia'
import { ref } from 'vue'

let _toastId = 0

export const useUiStore = defineStore('ui', () => {
  const toasts = ref([])
  const confirmDialog = ref(null)

  function toast(message, type = 'info', duration = 4000) {
    const id = ++_toastId
    toasts.value.push({ id, message, type })
    setTimeout(() => removeToast(id), duration)
  }

  function success(message) { toast(message, 'success') }
  function warn(message) { toast(message, 'warning') }
  function err(message) { toast(message, 'error', 6000) }
  function info(message) { toast(message, 'info') }

  function removeToast(id) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function confirm(options) {
    return new Promise((resolve) => {
      confirmDialog.value = { ...options, resolve }
    })
  }

  function closeConfirm(result) {
    if (confirmDialog.value) {
      confirmDialog.value.resolve(result)
      confirmDialog.value = null
    }
  }

  return { toasts, confirmDialog, toast, success, warn, err, info, removeToast, confirm, closeConfirm }
})
