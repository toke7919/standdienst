<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Backup</h1>

    <div class="max-w-2xl space-y-4">
      <div class="card space-y-4">
        <p class="text-sm text-gray-600">
          Erstellt einen verschlüsselten AES-256-Datenbank-Dump und überträgt ihn per SMB.
          Das automatische Backup läuft täglich um 02:30 Uhr.
        </p>
        <div class="flex gap-3">
          <button class="btn-secondary" :disabled="testing" @click="testConnection">
            <LoadingSpinner v-if="testing" size="sm" />
            Verbindung testen
          </button>
          <button class="btn-primary" :disabled="creating" @click="createBackup">
            <LoadingSpinner v-if="creating" size="sm" />
            Backup jetzt erstellen
          </button>
        </div>
        <p v-if="status" class="text-sm" :class="status.ok ? 'text-green-700' : 'text-red-600'">
          {{ status.message }}
        </p>
      </div>

      <div v-if="lastResult" class="card text-sm">
        <p class="font-medium mb-1">Letztes Backup</p>
        <p class="text-gray-600">Datei: <code class="font-mono text-xs">{{ lastResult.filename }}</code></p>
        <p class="text-gray-600">Größe: {{ (lastResult.size_bytes / 1024).toFixed(1) }} KB</p>
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
const testing = ref(false)
const creating = ref(false)
const status = ref(null)
const lastResult = ref(null)

async function testConnection() {
  testing.value = true
  status.value = null
  try {
    await adminApi.testSmbConnection()
    status.value = { ok: true, message: 'Verbindung erfolgreich' }
  } catch (e) {
    status.value = { ok: false, message: e.response?.data?.error || 'Verbindung fehlgeschlagen' }
  } finally {
    testing.value = false
  }
}

async function createBackup() {
  creating.value = true
  status.value = null
  try {
    const res = await adminApi.createBackup()
    lastResult.value = res.data.data
    status.value = { ok: true, message: res.data.message }
    ui.success('Backup erstellt')
  } catch (e) {
    status.value = { ok: false, message: e.response?.data?.error || 'Backup fehlgeschlagen' }
  } finally {
    creating.value = false
  }
}
</script>
