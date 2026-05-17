<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">System-Update</h1>

    <div class="max-w-2xl space-y-4">
      <div class="card space-y-4">
        <div v-if="checking" class="flex items-center gap-2 text-gray-500 text-sm">
          <LoadingSpinner size="sm" />
          Prüfe auf Updates…
        </div>

        <template v-else-if="updateInfo">
          <div class="flex items-center gap-3">
            <div>
              <p class="font-medium text-gray-900">Version: {{ updateInfo.current_version }}</p>
              <p class="text-sm text-gray-500 mt-0.5">
                {{ updateInfo.update_available
                  ? `${updateInfo.commits_behind} Commit(s) hinter origin/main`
                  : 'Aktuell — kein Update verfügbar' }}
              </p>
            </div>
            <span v-if="updateInfo.update_available" class="badge-blue ml-auto">Update verfügbar</span>
            <span v-else class="badge-green ml-auto">Aktuell</span>
          </div>

          <div class="flex gap-3">
            <button class="btn-secondary" @click="checkUpdate">Erneut prüfen</button>
            <button
              v-if="updateInfo.update_available"
              class="btn-primary"
              :disabled="applying"
              @click="applyUpdate"
            >
              <LoadingSpinner v-if="applying" size="sm" />
              Update anwenden
            </button>
          </div>
        </template>

        <button v-else class="btn-secondary" @click="checkUpdate">Auf Updates prüfen</button>
      </div>

      <div v-if="updateLog.length" class="card">
        <h2 class="text-sm font-semibold text-gray-700 mb-3">Protokoll</h2>
        <div class="space-y-2">
          <div v-for="(entry, i) in updateLog" :key="i" class="text-xs">
            <span :class="entry.ok ? 'text-green-700' : 'text-red-600'" class="font-medium">
              {{ entry.step }}
            </span>
            <pre v-if="entry.output" class="mt-1 text-gray-500 whitespace-pre-wrap">{{ entry.output }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const ui = useUiStore()
const checking = ref(false)
const applying = ref(false)
const updateInfo = ref(null)
const updateLog = ref([])

async function checkUpdate() {
  checking.value = true
  try {
    const res = await adminApi.checkUpdate()
    updateInfo.value = res.data.data
  } catch (e) {
    ui.err(e.response?.data?.error || 'Update-Check fehlgeschlagen')
  } finally {
    checking.value = false
  }
}

async function applyUpdate() {
  const ok = await ui.confirm({
    title: 'Update anwenden',
    message: 'Das System wird aktualisiert. Danach ist ein Neustart erforderlich. Fortfahren?',
    confirmText: 'Update starten',
  })
  if (!ok) return

  applying.value = true
  updateLog.value = []
  try {
    const res = await adminApi.applyUpdate()
    updateLog.value = res.data.data.log
    ui.success(res.data.message)
    updateInfo.value = null
  } catch (e) {
    ui.err(e.response?.data?.error || 'Update fehlgeschlagen')
    updateLog.value = e.response?.data?.errors?.log || []
  } finally {
    applying.value = false
  }
}
</script>
