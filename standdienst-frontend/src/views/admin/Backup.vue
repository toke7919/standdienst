<template>
  <div>
    <h1 class="text-2xl font-bold text-ink mb-6">Backup & Restore</h1>

    <div class="max-w-3xl space-y-4">
      <!-- Backup-Passwort Einstellungen -->
      <div class="card space-y-3">
        <h2 class="text-base font-semibold text-ink">Backup-Passwort</h2>
        <p class="text-xs text-muted">
          Alle Backups werden mit diesem Passwort verschlüsselt (AES-256-GCM). Ohne dieses Passwort
          können Backups nicht wiederhergestellt werden.
        </p>
        <div class="flex gap-2 items-end">
          <div class="flex-1">
            <input
              v-model="newPassword"
              type="password"
              class="input"
              :placeholder="hasPassword ? '●●●●●●●● (gesetzt)' : 'Neues Backup-Passwort'"
              autocomplete="new-password"
            />
          </div>
          <button class="btn-primary shrink-0" :disabled="savingPw || !newPassword" @click="savePassword">
            <LoadingSpinner v-if="savingPw" size="sm" />
            {{ hasPassword ? 'Ändern' : 'Speichern' }}
          </button>
        </div>
        <p v-if="!hasPassword" class="text-xs text-amber-700 bg-amber-50 rounded px-2 py-1">
          Kein Backup-Passwort konfiguriert – Backups können erst erstellt werden wenn ein Passwort gesetzt ist.
        </p>
      </div>

      <!-- Aktionen -->
      <div class="card flex flex-wrap gap-3 items-center">
        <button class="btn-primary" :disabled="creating || !hasPassword" @click="createBackup">
          <LoadingSpinner v-if="creating" size="sm" />
          Backup erstellen
        </button>
        <label class="btn-secondary cursor-pointer">
          <input type="file" accept=".sdbackup" class="hidden" @change="handleUpload" />
          Backup hochladen
        </label>
        <p class="text-xs text-muted ml-auto">
          Max. {{ maxBackups }} Backups – älteste werden automatisch gelöscht.
        </p>
      </div>

      <!-- Backup-Liste -->
      <div class="card overflow-hidden p-0">
        <div v-if="loading" class="flex justify-center py-8"><LoadingSpinner size="lg" /></div>
        <div v-else>
          <div v-if="!backups.length" class="px-4 py-8 text-center text-muted text-sm">
            Keine Backups vorhanden
          </div>
          <div v-for="b in backups" :key="b.filename"
               class="border-b border-sand last:border-0 hover:bg-bg-warm px-4 py-3">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex items-start gap-2">
                <!-- Lock-Icon -->
                <button
                  :title="b.locked ? 'Entsperren' : 'Sperren'"
                  class="mt-0.5 shrink-0"
                  :class="b.locked ? 'text-amber-500 hover:text-amber-700' : 'text-sand-400 hover:text-ink/40'"
                  @click="toggleLock(b)"
                >
                  <svg v-if="b.locked" xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path fill-rule="evenodd" d="M12 1.5a5.25 5.25 0 00-5.25 5.25v3a3 3 0 00-3 3v6.75a3 3 0 003 3h10.5a3 3 0 003-3v-6.75a3 3 0 00-3-3v-3c0-2.9-2.35-5.25-5.25-5.25zm3.75 8.25v-3a3.75 3.75 0 10-7.5 0v3h7.5z" clip-rule="evenodd" />
                  </svg>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18 1.5c2.9 0 5.25 2.35 5.25 5.25v3.75a.75.75 0 01-1.5 0V6.75a3.75 3.75 0 10-7.5 0v3h.75a3 3 0 013 3v6.75a3 3 0 01-3 3H3.75a3 3 0 01-3-3v-6.75a3 3 0 013-3H15v-3c0-2.9 2.35-5.25 5.25-5.25z" />
                  </svg>
                </button>
                <div class="min-w-0">
                  <p class="font-mono text-xs text-ink/80 truncate">{{ b.filename }}</p>
                  <p class="text-xs text-muted mt-0.5">
                    {{ fmt(b.created_at) }} &middot; {{ (b.size_bytes / 1024).toFixed(1) }} KB
                    <span v-if="b.locked" class="ml-1 text-amber-600 font-medium">· gesperrt</span>
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
                  class="text-primary-600 hover:underline text-xs whitespace-nowrap"
                  @click="restore(b.filename)"
                >Wiederherstellen</button>
                <button
                  class="text-red-500 hover:underline text-xs"
                  :class="b.locked ? 'opacity-30 cursor-not-allowed' : ''"
                  :disabled="b.locked"
                  @click="del(b)"
                >Löschen</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Restore-Modal -->
    <Teleport to="body">
      <div v-if="restoreTarget" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
        <div class="bg-soft rounded-md shadow-xl w-full max-w-md p-6 space-y-4">
          <h2 class="text-lg font-semibold text-ink">Backup wiederherstellen</h2>
          <p class="text-sm text-ink/80">
            Backup: <code class="font-mono text-xs bg-bg-brand px-1 rounded">{{ restoreTarget }}</code>
          </p>
          <p class="text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
            Alle aktuellen Daten werden überschrieben. Dieser Vorgang kann nicht rückgängig gemacht werden.
            Die Anwendung wird anschließend automatisch neu gestartet.
          </p>
          <div>
            <label class="label">Backup-Passwort</label>
            <input v-model="restoreBackupPw" type="password" class="input"
                   placeholder="Backup-Passwort" autocomplete="off" />
            <p class="text-xs text-muted mt-1">
              Für Migrationen: Passwort des Quell-Backups eingeben, falls abweichend.
            </p>
          </div>
          <div>
            <label class="label">Admin-Passwort zur Bestätigung</label>
            <input v-model="adminPassword" type="password" class="input"
                   placeholder="Dein aktuelles Passwort" autocomplete="current-password" />
          </div>
          <div class="flex gap-3">
            <button class="btn-secondary flex-1" @click="restoreTarget = null">Abbrechen</button>
            <button class="btn-primary flex-1 bg-red-600 hover:bg-red-700"
                    :disabled="restoring || !adminPassword || !restoreBackupPw"
                    @click="confirmRestore">
              <LoadingSpinner v-if="restoring" size="sm" />
              Wiederherstellen
            </button>
          </div>
        </div>
      </div>
    </Teleport>
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
const savingPw = ref(false)
const backups = ref([])
const maxBackups = ref(20)
const hasPassword = ref(false)
const newPassword = ref('')
const restoreTarget = ref(null)
const restoreBackupPw = ref('')
const adminPassword = ref('')

function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

onMounted(async () => {
  await Promise.all([loadSettings(), loadList()])
})

async function loadSettings() {
  try {
    const res = await adminApi.getBackupSettings()
    hasPassword.value = res.data.data.has_backup_password
  } catch {
    // ignore
  }
}

async function loadList() {
  loading.value = true
  try {
    const res = await adminApi.listBackups()
    backups.value = res.data.data.backups
    maxBackups.value = res.data.data.max_backups ?? 20
  } catch {
    ui.err('Backupliste konnte nicht geladen werden')
  } finally {
    loading.value = false
  }
}

async function savePassword() {
  if (!newPassword.value.trim()) return
  savingPw.value = true
  try {
    await adminApi.updateBackupSettings({ backup_password: newPassword.value.trim() })
    hasPassword.value = true
    newPassword.value = ''
    ui.success('Backup-Passwort gesetzt')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler beim Speichern')
  } finally {
    savingPw.value = false
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

async function del(b) {
  if (b.locked) return
  const ok = await ui.confirm({
    title: 'Backup löschen',
    message: `"${b.filename}" unwiderruflich löschen?`,
    confirmText: 'Löschen',
  })
  if (!ok) return
  try {
    const res = await adminApi.deleteBackup(b.filename)
    backups.value = res.data.data.backups
    ui.success('Backup gelöscht')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Löschen fehlgeschlagen')
  }
}

async function toggleLock(b) {
  try {
    const res = b.locked
      ? await adminApi.unlockBackup(b.filename)
      : await adminApi.lockBackup(b.filename)
    backups.value = res.data.data.backups
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}

function restore(name) {
  restoreTarget.value = name
  restoreBackupPw.value = ''
  adminPassword.value = ''
}

async function confirmRestore() {
  restoring.value = true
  try {
    await adminApi.restoreBackup(restoreTarget.value, {
      admin_password: adminPassword.value,
      backup_password: restoreBackupPw.value,
    })
    ui.success('Backup wiederhergestellt – Anwendung wird neu gestartet')
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
