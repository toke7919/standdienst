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

    <!-- Restore-Bestätigungs-Modal -->
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

    <!-- Fortschritts-Modal -->
    <Teleport to="body">
      <div v-if="progressJobId" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
        <div class="bg-soft rounded-md shadow-xl w-full max-w-md p-6 space-y-5">
          <h2 class="text-lg font-semibold text-ink">Backup wird wiederhergestellt</h2>

          <!-- Fehlerfall -->
          <div v-if="progressError" class="space-y-4">
            <div class="flex items-start gap-3 text-red-600 bg-red-50 rounded-lg px-3 py-3">
              <svg class="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="currentColor">
                <path fill-rule="evenodd" d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zm-1.72 6.97a.75.75 0 10-1.06 1.06L10.94 12l-1.72 1.72a.75.75 0 101.06 1.06L12 13.06l1.72 1.72a.75.75 0 101.06-1.06L13.06 12l1.72-1.72a.75.75 0 10-1.06-1.06L12 10.94l-1.72-1.72z" clip-rule="evenodd" />
              </svg>
              <div>
                <p class="font-medium text-sm">Wiederherstellung fehlgeschlagen</p>
                <p class="text-xs mt-1 text-red-500 font-mono break-all">{{ progressError }}</p>
              </div>
            </div>
            <button class="btn-secondary w-full" @click="closeProgressModal">Schließen</button>
          </div>

          <!-- Laufend / Abgeschlossen -->
          <div v-else class="space-y-4">
            <!-- Fortschrittsbalken -->
            <div>
              <div class="flex justify-between items-center mb-1.5">
                <span class="text-sm text-ink/80">{{ progressMessage }}</span>
                <span class="text-xs tabular-nums font-semibold text-muted">{{ progressPct }}%</span>
              </div>
              <div class="h-2.5 bg-bg-brand rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="progressDone ? 'bg-emerald-500' : 'bg-primary-500'"
                  :style="`width: ${progressPct}%`"
                />
              </div>
            </div>

            <!-- Schritt-Liste -->
            <div class="space-y-2">
              <div v-for="step in RESTORE_STEPS" :key="step.key"
                   class="flex items-center gap-2.5 text-xs">
                <!-- Erledigt -->
                <svg v-if="stepIsDone(step.key)" class="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                  <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clip-rule="evenodd" />
                </svg>
                <!-- Aktiv (pulsierend) -->
                <div v-else-if="stepIsActive(step.key)"
                     class="w-3.5 h-3.5 rounded-full border-2 border-primary-500 flex-shrink-0 animate-pulse" />
                <!-- Ausstehend -->
                <div v-else class="w-3.5 h-3.5 rounded-full border border-sand flex-shrink-0" />

                <span :class="{
                  'text-ink font-medium': stepIsActive(step.key),
                  'text-muted line-through': stepIsDone(step.key),
                  'text-muted': !stepIsActive(step.key) && !stepIsDone(step.key),
                }">{{ step.label }}</span>
              </div>
            </div>

            <!-- Hinweis während Datenbank-Restore -->
            <p v-if="progressStep === 'db_restore'"
               class="text-xs text-amber-700 bg-amber-50 rounded px-2.5 py-1.5">
              Die Datenbankwiederherstellung kann je nach Datenmenge mehrere Minuten dauern.
            </p>

            <!-- Abgeschlossen: Countdown -->
            <div v-if="progressDone"
                 class="pt-3 border-t border-sand text-center text-sm text-muted">
              <svg class="w-6 h-6 text-emerald-500 mx-auto mb-1.5" viewBox="0 0 24 24" fill="currentColor">
                <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clip-rule="evenodd" />
              </svg>
              <p class="font-medium text-emerald-700">Erfolgreich wiederhergestellt</p>
              <p class="text-xs mt-1">Seite lädt in {{ countdown }} Sekunden neu …</p>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
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

// Fortschritt
const progressJobId = ref(null)
const progressStep = ref('')
const progressPct = ref(0)
const progressMessage = ref('')
const progressDone = ref(false)
const progressError = ref(null)
const countdown = ref(5)

let pollTimer = null
let countdownTimer = null
let pollStartTime = 0

const RESTORE_STEPS = [
  { key: 'decrypt',     label: 'Entschlüssele Backup' },
  { key: 'extract',     label: 'Entpacke Archiv' },
  { key: 'db_restore',  label: 'Stelle Datenbank wieder her' },
  { key: 'credentials', label: 'Verschlüssele Zugangsdaten' },
  { key: 'uploads',     label: 'Stelle Dateien wieder her' },
  { key: 'restart',     label: 'Starte Anwendung neu' },
]
const STEP_ORDER = RESTORE_STEPS.map(s => s.key)

function stepIsDone(key) {
  if (progressDone.value && !progressError.value) return true
  const cur = STEP_ORDER.indexOf(progressStep.value)
  return STEP_ORDER.indexOf(key) < cur
}
function stepIsActive(key) {
  return progressStep.value === key
}

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

onUnmounted(() => {
  stopPolling()
})

async function loadSettings() {
  try {
    const res = await adminApi.getBackupSettings()
    hasPassword.value = res.data.data.has_backup_password
  } catch { /* ignore */ }
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
    const res = await adminApi.restoreBackup(restoreTarget.value, {
      admin_password: adminPassword.value,
      backup_password: restoreBackupPw.value,
    })
    const jobId = res.data.data.job_id
    restoreTarget.value = null
    openProgressModal(jobId)
  } catch (e) {
    ui.err(e.response?.data?.error || 'Restore konnte nicht gestartet werden')
  } finally {
    restoring.value = false
  }
}

function openProgressModal(jobId) {
  progressJobId.value = jobId
  progressStep.value = 'starting'
  progressPct.value = 0
  progressMessage.value = 'Starte Wiederherstellung …'
  progressDone.value = false
  progressError.value = null
  countdown.value = 5
  pollStartTime = Date.now()
  startPolling(jobId)
}

function startPolling(jobId) {
  pollTimer = setInterval(async () => {
    try {
      const res = await adminApi.getRestoreStatus(jobId)
      const s = res.data.data
      progressStep.value = s.step
      progressPct.value = s.progress
      progressMessage.value = s.message
      progressDone.value = s.done
      progressError.value = s.error || null

      if (s.done && !s.error) {
        stopPolling()
        countdown.value = 5
        countdownTimer = setInterval(() => {
          countdown.value--
          if (countdown.value <= 0) {
            clearInterval(countdownTimer)
            window.location.reload()
          }
        }, 1000)
      } else if (s.done && s.error) {
        stopPolling()
      }
    } catch {
      // Netzwerkfehler – App wird vermutlich gerade neu gestartet
      if (Date.now() - pollStartTime > 15_000) {
        stopPolling()
        window.location.reload()
      }
    }
  }, 700)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function closeProgressModal() {
  stopPolling()
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
  progressJobId.value = null
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
