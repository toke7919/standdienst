<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Termine</h1>
      <button class="btn-primary" @click="openCreate">Neuer Termin</button>
    </div>

    <div class="card space-y-2">
      <div
        v-for="d in dates"
        :key="d.id"
        class="flex items-center justify-between p-3 rounded-lg border border-gray-100 bg-gray-50"
      >
        <div>
          <p class="font-medium text-gray-900">{{ d.formatted }}</p>
          <p v-if="d.label" class="text-xs text-gray-500">{{ d.label }}</p>
        </div>
        <div class="flex gap-2">
          <button class="text-xs text-primary-600 hover:underline" @click="openEdit(d)">Bearbeiten</button>
          <button class="text-xs text-red-600 hover:underline" @click="deleteDate(d)">Löschen</button>
        </div>
      </div>
      <p v-if="!dates.length" class="text-center text-gray-400 py-8">Noch keine Termine</p>
    </div>

    <Modal v-model="showModal" :title="editing ? 'Termin bearbeiten' : 'Neuer Termin'">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="label">Datum</label>
          <input v-model="form.date" type="date" class="input" required />
        </div>
        <div>
          <label class="label">Beschriftung (optional)</label>
          <input v-model="form.label" class="input" placeholder="z.B. Aufbautag" />
        </div>
        <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
        <div class="flex gap-3 justify-end pt-2">
          <button type="button" class="btn-secondary" @click="showModal = false">Abbrechen</button>
          <button type="submit" class="btn-primary">Speichern</button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import Modal from '@/components/Modal.vue'

const route = useRoute()
const ui = useUiStore()
const dates = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ date: '', label: '' })
const saveError = ref('')

onMounted(load)

async function load() {
  const res = await adminApi.getDates(route.params.slug)
  dates.value = res.data.data
}

function openCreate() {
  editing.value = null
  form.value = { date: '', label: '' }
  saveError.value = ''
  showModal.value = true
}

function openEdit(d) {
  editing.value = d
  form.value = { date: d.date, label: d.label || '' }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateDate(route.params.slug, editing.value.id, form.value)
      ui.success('Termin aktualisiert')
    } else {
      await adminApi.createDate(route.params.slug, form.value)
      ui.success('Termin erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteDate(d) {
  const ok = await ui.confirm({
    title: 'Termin löschen', message: `${d.formatted} löschen?`, confirmText: 'Löschen', danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteDate(route.params.slug, d.id)
    ui.success('Gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
