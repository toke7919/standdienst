<template>
  <div>
    <RouterView />
    <ToastContainer />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { RouterView, useRouter, useRoute } from 'vue-router'
import { setupApi } from '@/api/setup'
import { useSetupStore } from '@/stores/setup'
import ToastContainer from '@/components/ToastContainer.vue'

const router = useRouter()
const route = useRoute()
const setup = useSetupStore()

let _interval = null

onMounted(() => {
  _interval = setInterval(async () => {
    try {
      const res = await setupApi.status()
      const mode = res.data.data.maintenance_mode ?? false
      if (mode !== setup.maintenanceMode) {
        setup.setMaintenance(mode)
        if (mode && !route.path.startsWith('/admin') && !route.meta?.maintenance) {
          router.push('/maintenance')
        } else if (!mode && route.meta?.maintenance) {
          router.push('/')
        }
      }
    } catch { /* ignore */ }
  }, 60_000)
})

onUnmounted(() => {
  clearInterval(_interval)
})
</script>
