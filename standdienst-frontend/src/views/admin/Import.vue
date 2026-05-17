<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Import</h1>

    <div class="max-w-2xl space-y-6">
      <div class="card">
        <h2 class="text-base font-semibold text-gray-800 mb-2">Vorlagen herunterladen</h2>
        <p class="text-sm text-gray-500 mb-4">
          Lade eine Vorlage herunter, fülle sie aus und importiere sie unten.
        </p>
        <div class="flex gap-3">
          <a :href="adminApi.importTemplateCsvUrl(slug)" class="btn-secondary text-sm">
            CSV-Vorlage
          </a>
          <a :href="adminApi.importTemplateXlsxUrl(slug)" class="btn-secondary text-sm">
            XLSX-Vorlage
          </a>
        </div>
      </div>

      <div class="card">
        <h2 class="text-base font-semibold text-gray-800 mb-4">Schichten importieren</h2>
        <div class="space-y-3">
          <div>
            <label class="label">Datei auswählen (CSV, XLSX oder ODS)</label>
            <input ref="fileInput" type="file" accept=".csv,.xlsx,.ods" class="text-sm" @change="onFileChange" />
          </div>
          <p v-if="result" class="text-sm" :class="result.error ? 'text-red-600' : 'text-green-700'">
            {{ result.message }}
          </p>
          <div v-if="result?.errors?.length" class="text-xs text-red-600 space-y-0.5">
            <p v-for="(e, i) in result.errors" :key="i">{{ e }}</p>
          </div>
          <button class="btn-primary" :disabled="!selectedFile || importing" @click="doImport">
            <LoadingSpinner v-if="importing" size="sm" />
            Importieren
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const slug = computed(() => route.params.slug)
const selectedFile = ref(null)
const importing = ref(false)
const result = ref(null)

function onFileChange(e) {
  selectedFile.value = e.target.files[0] || null
  result.value = null
}

async function doImport() {
  if (!selectedFile.value) return
  importing.value = true
  result.value = null
  const fd = new FormData()
  fd.append('file', selectedFile.value)
  const name = selectedFile.value.name.toLowerCase()

  try {
    let res
    if (name.endsWith('.xlsx')) {
      res = await adminApi.importShiftsXlsx(slug.value, fd)
    } else if (name.endsWith('.ods')) {
      res = await adminApi.importShiftsOds(slug.value, fd)
    } else {
      res = await adminApi.importShiftsCsv(slug.value, fd)
    }
    result.value = { message: res.data.message, errors: res.data.data?.errors }
    ui.success(res.data.message)
  } catch (e) {
    result.value = { error: true, message: e.response?.data?.error || 'Import fehlgeschlagen' }
  } finally {
    importing.value = false
  }
}
</script>
