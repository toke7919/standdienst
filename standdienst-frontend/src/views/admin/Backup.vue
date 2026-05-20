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
        <label class="btn-secondary cursor-pointer">
          <input type="file" accept=".enc" class="hidden" @change="handleUpload" />
          Backup hochladen
        </label>
        <p class="text-xs text-gray-400 ml-auto">
          Max. {{ maxBackups }} Backups – älteste werden automatisch gelöscht.
        </p>
      </div>

      <!-- Backup-Liste -->
      <div class="card overflow-hidden p-0">
        <div v-if="loading" class="flex justify-center py-8"><LoadingSpinner size="lg" /></div>
        <div v-else>
          <div v-if="!backups.length" class="px-4 py-8 text-center text-gray-400 text-sm">
            Keine Backups vorhanden
          </div>
          <div v-for="b in backups" :key="b.filename"
               class="border-b border-gray-100 last:border-0 hover:bg-gray-50 px-4 py-3">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex items-start gap-2">
                <span
                  class="mt-0.5 flex-shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded"
                  :class="b.type === 'encrypted'
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-500'"
                  :title="b.type === 'encrypted' ? 'In-App-Backup (verschlüsselt, wiederherstellbar)' : 'Shell-Skript-Backup (SQL, nur Download)'"
                >{{ b.type === 'encrypted' ? 'App' : 'Skript' }}</span>
                <div class="min-w-0">
                  <p class="font-mono text-xs text-gray-700 truncate">{{ b.filename }}</p>
                  <p class="text-xs text-gray-400 mt-0.5">
                    {{ fmt(b.created_at) }} &middot; {{ (b.size_bytes / 1024).toFixed(1) }} KB
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-3 shrink-0">
                <a
                  :href="adminApi.downloadBackupUrl(b.filename)"
                  download
                  class="text-green-600 hover:underline text-xs whitespace-nowrap"
                >Herunterladen</a>
                <button
                  v-if="b.type === 'encrypted'"
                  class="text-indigo-600 hover:underline text-xs whitespace-nowrap"
                  @click="restore(b.filename)"
                >Wiederherstellen</button>
                <button class="text-red-500 hover:underline text-xs" @click="del(b.filename)">
                  Löschen
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Restore-Modal -->
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
          <label class="label">Admin-Passwort zur Bestätigung</label>
          <input v-model="adminPassword" type="password" class="input"
                 placeholder="Dein aktuelles Passwort" autocomplete="current-password" />
        </div>
        <div class="flex gap-3">
          <button class="btn-secondary flex-1" @click="restoreTarget = null">Abbrechen</button>
          <button class="btn-primary flex-1 bg-red-600 hover:bg-red-700"
                  :disabled="restoring || !adminPassword" @click="confirmRestore">
            <LoadingSpinner v-if="restoring" size="sm" />
            Wiederherstellen
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const ui = useUiStore()
const loading = ref(true)
const creating = ref(false)
const restoring = ref(false)
const backups = ref([])
const maxBackups = 10
const restoreTarget = ref(null)
const adminPassword = ref('')

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
  adminPassword.value = ''
}

async function confirmRestore() {
  restoring.value = true
  try {
    await adminApi.restoreBackup(restoreTarget.value, { admin_password: adminPassword.value })
    ui.success('Datenbank wiederhergestellt – bitte Seite neu laden')
    restoreTarget.value = null
  } catch (e) {
    ui.err(e.response?.data?.error || 'Restore fehlgeschlagen')
  } finally {
    restoring.value = false
  }
}

async function handleUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await adminApi.uploadBackup(fd)
    backups.value = res.data.data.backups
    ui.success('Backup hochgeladen')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Upload fehlgeschlagen')
  }
  event.target.value = ''
}
</script>
