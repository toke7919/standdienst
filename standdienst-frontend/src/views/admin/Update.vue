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
          <!-- Installierte Version -->
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Installierte Version</p>
              <p class="font-semibold text-gray-900 text-lg font-mono">{{ updateInfo.current_version }}</p>
            </div>
            <span v-if="updateInfo.update_available" class="badge-blue">Update verfügbar</span>
            <span v-else class="badge-green">Aktuell</span>
          </div>

          <!-- Release-Notes installierte Version -->
          <div v-if="updateInfo.current_release_notes" class="border border-gray-100 rounded-lg">
            <button type="button"
                    class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg"
                    @click="showCurrentNotes = !showCurrentNotes">
              Release-Notes {{ updateInfo.current_version }}
              <span class="text-gray-400 text-xs">{{ showCurrentNotes ? '▲' : '▼' }}</span>
            </button>
            <div v-if="showCurrentNotes" class="px-4 pb-4 pt-1 text-sm text-gray-600 whitespace-pre-wrap border-t border-gray-100">
              {{ updateInfo.current_release_notes }}
            </div>
          </div>

          <!-- Neueste Version (wenn Update verfügbar) -->
          <template v-if="updateInfo.update_available">
            <div class="border-t border-gray-100 pt-4">
              <p class="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Neue Version</p>
              <p class="font-semibold text-indigo-700 text-lg font-mono">{{ updateInfo.latest_version }}</p>
            </div>
            <div v-if="updateInfo.latest_release_notes" class="border border-indigo-100 rounded-lg bg-indigo-50/50">
              <button type="button"
                      class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-indigo-700 hover:bg-indigo-50 rounded-lg"
                      @click="showLatestNotes = !showLatestNotes">
                Release-Notes {{ updateInfo.latest_version }}
                <span class="text-indigo-400 text-xs">{{ showLatestNotes ? '▲' : '▼' }}</span>
              </button>
              <div v-if="showLatestNotes" class="px-4 pb-4 pt-1 text-sm text-gray-600 whitespace-pre-wrap border-t border-indigo-100">
                {{ updateInfo.latest_release_notes }}
              </div>
            </div>
          </template>

          <div class="flex gap-3 pt-2">
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
const showCurrentNotes = ref(false)
const showLatestNotes = ref(true)

async function checkUpdate() {
  checking.value = true
  try {
    const res = await adminApi.checkUpdate()
    updateInfo.value = res.data.data
    showCurrentNotes.value = false
    showLatestNotes.value = !!updateInfo.value?.update_available
  } catch (e) {
    ui.err(e.response?.data?.error || 'Update-Check fehlgeschlagen')
  } finally {
    checking.value = false
  }
}

async function applyUpdate() {
  const confirmed = await ui.confirm({
    title: 'Update anwenden',
    message: 'Das System wird aktualisiert. Danach ist ein Neustart erforderlich. Fortfahren?',
    confirmText: 'Update starten',
  })
  if (!confirmed) return

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
