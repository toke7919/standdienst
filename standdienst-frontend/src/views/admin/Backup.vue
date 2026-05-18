<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Backup & Restore</h1>

    <div class="max-w-3xl space-y-4">
      <!-- Aktionen -->
      <div class="card flex flex-wrap gap-3 items-center">
        <button class="btn-primary" :disabled="creating" @click="createBackup">
          <LoadingSpinner v-if="creating" size="sm" />
          Backup erstellen
        </button>
        <button class="btn-secondary" @click="showKeyModal = true">
          Verschlüsselungsschlüssel exportieren
        </button>
        <p class="text-xs text-gray-400 ml-auto">
          Max. {{ maxBackups }} Backups – älteste werden automatisch gelöscht.
        </p>
      </div>

      <!-- Backup-Liste -->
      <div class="card overflow-hidden p-0">
        <div v-if="loading" class="flex justify-center py-8"><LoadingSpinner size="lg" /></div>
        <table v-else class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-100">
            <tr>
              <th class="px-4 py-3 text-left font-medium text-gray-500">Datei</th>
              <th class="px-4 py-3 text-left font-medium text-gray-500">Erstellt</th>
              <th class="px-4 py-3 text-left font-medium text-gray-500">Größe</th>
              <th class="px-4 py-3 text-left font-medium text-gray-500">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in backups" :key="b.filename" class="border-b border-gray-50 hover:bg-gray-50">
              <td class="px-4 py-3 font-mono text-xs text-gray-700">{{ b.filename }}</td>
              <td class="px-4 py-3 text-gray-500 whitespace-nowrap">{{ fmt(b.created_at) }}</td>
              <td class="px-4 py-3 text-gray-400">{{ (b.size_bytes / 1024).toFixed(1) }} KB</td>
              <td class="px-4 py-3 flex gap-2">
                <button class="text-indigo-600 hover:underline text-xs" @click="restore(b.filename)">
                  Wiederherstellen
                </button>
                <button class="text-red-500 hover:underline text-xs" @click="del(b.filename)">
                  Löschen
                </button>
              </td>
            </tr>
            <tr v-if="!backups.length">
              <td colspan="4" class="px-4 py-8 text-center text-gray-400">Keine Backups vorhanden</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Key-Export-Modal -->
    <div v-if="showKeyModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 class="text-lg font-semibold text-gray-900">Verschlüsselungsschlüssel</h2>
        <p class="text-sm text-gray-600">
          Bewahre diesen Schlüssel sicher auf. Er wird benötigt, um Backups auf einer anderen
          Installation wiederherzustellen.
        </p>
        <div v-if="exportedKey">
          <textarea class="input font-mono text-xs" rows="3" readonly :value="exportedKey" @click="$event.target.select()" />
          <p class="text-xs text-gray-400 mt-1">Klicken zum Markieren</p>
        </div>
        <div v-else class="flex justify-center py-4"><LoadingSpinner size="lg" /></div>
        <button class="btn-secondary w-full" @click="showKeyModal = false">Schließen</button>
      </div>
    </div>

    <!-- Restore-mit-Schlüssel-Modal -->
    <div v-if="restoreTarget" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 class="text-lg font-semibold text-gray-900">Datenbank wiederherstellen</h2>
        <p class="text-sm text-gray-600">
          Backup: <code class="font-mono text-xs bg-gray-100 px-1 rounded">{{ restoreTarget }}</code>
        </p>
        <p class="text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
          Alle aktuellen Daten werden überschrieben. Dieser Vorgang kann nicht rückgängig gemacht werden.
        </p>
        <div>
          <label class="label">Schlüssel (nur bei Fremd-Backup)</label>
          <input v-model="restoreKey" class="input font-mono text-xs"
                 placeholder="Leer lassen = aktueller Schlüssel dieser Installation" />
        </div>
        <div class="flex gap-3">
          <button class="btn-secondary flex-1" @click="restoreTarget = null">Abbrechen</button>
          <button class="btn-primary flex-1 bg-red-600 hover:bg-red-700" :disabled="restoring" @click="confirmRestore">
            <LoadingSpinner v-if="restoring" size="sm" />
            Wiederherstellen
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const ui = useUiStore()
const loading = ref(true)
const creating = ref(false)
const restoring = ref(false)
const backups = ref([])
const maxBackups = 10
const showKeyModal = ref(false)
const exportedKey = ref(null)
const restoreTarget = ref(null)
const restoreKey = ref('')

function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(loadList)

async function loadList() {
  loading.value = true
  try {
    const res = await adminApi.listBackups()
    backups.value = res.data.data.backups
  } catch (e) {
    ui.err('Backupliste konnte nicht geladen werden')
  } finally {
    loading.value = false
  }
}

async function createBackup() {
  creating.value = true
  try {
    const res = await adminApi.createBackup()
    backups.value = res.data.data.backups
    ui.success('Backup erstellt')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Backup fehlgeschlagen')
  } finally {
    creating.value = false
  }
}

async function del(name) {
  const ok = await ui.confirm({
    title: 'Backup löschen',
    message: `"${name}" unwiderruflich löschen?`,
    confirmText: 'Löschen',
  })
  if (!ok) return
  try {
    const res = await adminApi.deleteBackup(name)
    backups.value = res.data.data.backups
    ui.success('Backup gelöscht')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Löschen fehlgeschlagen')
  }
}

function restore(name) {
  restoreTarget.value = name
  restoreKey.value = ''
}

async function confirmRestore() {
  restoring.value = true
  try {
    await adminApi.restoreBackup(restoreTarget.value, restoreKey.value ? { key: restoreKey.value } : {})
    ui.success('Datenbank wiederhergestellt – bitte Seite neu laden')
    restoreTarget.value = null
  } catch (e) {
    ui.err(e.response?.data?.error || 'Restore fehlgeschlagen')
  } finally {
    restoring.value = false
  }
}

watch(showKeyModal, async (open) => {
  if (!open) return
  exportedKey.value = null
  try {
    const res = await adminApi.exportBackupKey()
    exportedKey.value = res.data.data.key
  } catch (e) {
    ui.err('Schlüssel konnte nicht exportiert werden')
    showKeyModal.value = false
  }
})
</script>
