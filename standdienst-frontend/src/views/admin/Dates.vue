<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Termine</h1>
      <button class="btn-primary" @click="openCreate">Neuer Termin</button>
    </div>

    <div class="space-y-2">
      <div
        v-for="d in dates"
        :key="d.id"
        class="group bg-white rounded-xl border border-gray-100 shadow-sm px-5 py-4 flex items-center gap-4 hover:border-primary-200 transition-colors duration-150"
      >
        <div class="w-10 h-10 rounded-xl bg-violet-100 flex items-center justify-center flex-shrink-0">
          <CalendarIcon class="w-5 h-5 text-violet-600" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-gray-900">{{ d.formatted }}</p>
          <p v-if="d.label" class="text-sm text-gray-500 mt-0.5">{{ d.label }}</p>
        </div>
        <div class="flex items-center gap-3">
          <button class="text-sm text-primary-600 hover:text-primary-800 font-medium" @click="openEdit(d)">Bearbeiten</button>
          <span class="text-gray-200">|</span>
          <button class="text-sm text-red-500 hover:text-red-700 font-medium" @click="deleteDate(d)">Löschen</button>
        </div>
      </div>

      <div v-if="!dates.length" class="bg-white rounded-xl border border-gray-100 shadow-sm py-16 text-center">
        <CalendarIcon class="w-10 h-10 text-gray-200 mx-auto mb-3" />
        <p class="text-gray-400 text-sm">Noch keine Termine angelegt</p>
      </div>
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
import { CalendarIcon } from '@heroicons/vue/24/outline'

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
