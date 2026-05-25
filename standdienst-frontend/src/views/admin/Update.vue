<template>
  <div>
    <h1 class="text-2xl font-bold text-ink mb-6">System-Update</h1>

    <div class="max-w-2xl space-y-4">
      <div class="card space-y-4">
        <div v-if="checking" class="flex items-center gap-2 text-muted text-sm">
          <LoadingSpinner size="sm" />
          Prüfe auf Updates…
        </div>

        <template v-else-if="updateInfo">
          <!-- Installierte Version -->
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs text-muted uppercase tracking-wide mb-0.5">Installierte Version</p>
              <p class="font-semibold text-ink text-lg font-mono">{{ updateInfo.current_version }}</p>
            </div>
            <span v-if="updateInfo.update_available" class="badge-blue">Update verfügbar</span>
            <span v-else class="badge-green">Aktuell</span>
          </div>

          <!-- Hinweis wenn GitHub-Repo nicht konfiguriert -->
          <div v-if="updateInfo.error" class="text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
            {{ updateInfo.error }}
            <RouterLink to="/admin/settings/global" class="underline ml-1">Jetzt konfigurieren →</RouterLink>
          </div>

          <!-- Release-Notes installierte Version -->
          <div v-if="updateInfo.current_release_notes" class="border border-sand rounded-lg">
            <button type="button"
                    class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-ink/80 hover:bg-bg-warm rounded-lg"
                    @click="showCurrentNotes = !showCurrentNotes">
              Release-Notes {{ updateInfo.current_version }}
              <span class="text-muted text-xs">{{ showCurrentNotes ? '▲' : '▼' }}</span>
            </button>
            <div v-if="showCurrentNotes" class="px-4 pb-4 pt-1 text-sm text-ink/80 whitespace-pre-wrap border-t border-sand">
              {{ updateInfo.current_release_notes }}
            </div>
          </div>

          <!-- Neueste Version (wenn Update verfügbar) -->
          <template v-if="updateInfo.update_available">
            <div class="border-t border-sand pt-4">
              <p class="text-xs text-muted uppercase tracking-wide mb-0.5">Neue Version</p>
              <p class="font-semibold text-primary-700 text-lg font-mono">{{ updateInfo.latest_version }}</p>
            </div>
            <div v-if="updateInfo.latest_release_notes" class="border border-primary-200 rounded-lg bg-primary-50/50">
              <button type="button"
                      class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-primary-700 hover:bg-primary-50 rounded-lg"
                      @click="showLatestNotes = !showLatestNotes">
                Release-Notes {{ updateInfo.latest_version }}
                <span class="text-primary-400 text-xs">{{ showLatestNotes ? '▲' : '▼' }}</span>
              </button>
              <div v-if="showLatestNotes" class="px-4 pb-4 pt-1 text-sm text-ink/80 whitespace-pre-wrap border-t border-primary-200">
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
        <h2 class="text-sm font-semibold text-ink/80 mb-3">Protokoll</h2>
        <div class="space-y-2">
          <div v-for="(entry, i) in updateLog" :key="i" class="text-xs">
            <span :class="entry.ok ? 'text-green-700' : 'text-red-600'" class="font-medium">
              {{ entry.step }}
            </span>
            <pre v-if="entry.output" class="mt-1 text-muted whitespace-pre-wrap">{{ entry.output }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
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

onMounted(checkUpdate)

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
