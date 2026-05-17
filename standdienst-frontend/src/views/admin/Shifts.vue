<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Schichten</h1>
      <button class="btn-primary" @click="openCreate">Neue Schicht</button>
    </div>

    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Stand</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Datum</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Zeit</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Belegung</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in shifts" :key="s.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3 font-medium">{{ s.stand_name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ s.date_formatted }}</td>
            <td class="px-4 py-3 text-gray-500">{{ s.time_range }}</td>
            <td class="px-4 py-3">
              <span :class="s.is_full ? 'badge-red' : 'badge-green'">
                {{ s.current_count }}/{{ s.max_volunteers }}
              </span>
            </td>
            <td class="px-4 py-3 text-right space-x-2">
              <button class="text-xs text-primary-600 hover:underline" @click="openEdit(s)">Bearbeiten</button>
              <button class="text-xs text-red-600 hover:underline" @click="deleteShift(s)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-model:page="page" :pages="pages" :total="total" :per-page="20" @update:page="load" />

    <Modal v-model="showModal" :title="editing ? 'Schicht bearbeiten' : 'Neue Schicht'">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="label">Stand</label>
          <select v-model="form.stand_id" class="input" required>
            <option value="">Bitte wählen</option>
            <option v-for="s in stands" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div>
          <label class="label">Datum</label>
          <select v-model="form.event_date_id" class="input" required>
            <option value="">Bitte wählen</option>
            <option v-for="d in dates" :key="d.id" :value="d.id">{{ d.formatted }}</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Von</label>
            <input v-model="form.start_time" type="time" class="input" required />
          </div>
          <div>
            <label class="label">Bis</label>
            <input v-model="form.end_time" type="time" class="input" required />
          </div>
        </div>
        <div>
          <label class="label">Max. Helfer</label>
          <input v-model.number="form.max_volunteers" type="number" min="1" class="input" required />
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
import Pagination from '@/components/Pagination.vue'

const route = useRoute()
const ui = useUiStore()
const shifts = ref([])
const stands = ref([])
const dates = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const showModal = ref(false)
const editing = ref(null)
const form = ref({ stand_id: '', event_date_id: '', start_time: '08:00', end_time: '12:00', max_volunteers: 2 })
const saveError = ref('')

onMounted(async () => {
  await Promise.all([load(), loadMeta()])
})

async function load() {
  const res = await adminApi.getShifts(route.params.slug, { page: page.value, per_page: 20 })
  shifts.value = res.data.data
  pages.value = res.data.pages
  total.value = res.data.total
}

async function loadMeta() {
  const [sRes, dRes] = await Promise.all([
    adminApi.getStands(route.params.slug),
    adminApi.getDates(route.params.slug),
  ])
  stands.value = sRes.data.data
  dates.value = dRes.data.data
}

function openCreate() {
  editing.value = null
  form.value = { stand_id: '', event_date_id: '', start_time: '08:00', end_time: '12:00', max_volunteers: 2 }
  saveError.value = ''
  showModal.value = true
}

function openEdit(s) {
  editing.value = s
  form.value = {
    stand_id: s.stand_id, event_date_id: s.event_date_id,
    start_time: s.start_time, end_time: s.end_time, max_volunteers: s.max_volunteers,
  }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateShift(route.params.slug, editing.value.id, form.value)
      ui.success('Schicht aktualisiert')
    } else {
      await adminApi.createShift(route.params.slug, form.value)
      ui.success('Schicht erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteShift(s) {
  const ok = await ui.confirm({
    title: 'Schicht löschen', message: 'Schicht und alle Anmeldungen löschen?',
    confirmText: 'Löschen', danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteShift(route.params.slug, s.id)
    ui.success('Gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
