<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Anmeldungen</h1>
      <button class="btn-primary" @click="openCreate">Anmeldung hinzufügen</button>
    </div>

    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Helfer</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Stand</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Datum / Zeit</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Quelle</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in registrations" :key="r.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3 font-medium">{{ r.volunteer_name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ r.stand_name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ r.date_formatted }} {{ r.time_range }}</td>
            <td class="px-4 py-3">
              <span :class="r.registered_by_admin ? 'badge-blue' : 'badge-green'">
                {{ r.registered_by_admin ? 'Admin' : 'Helfer' }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <button class="text-xs text-red-600 hover:underline" @click="deleteReg(r)">Entfernen</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-model:page="page" :pages="pages" :total="total" :per-page="20" @update:page="load" />

    <Modal v-model="showModal" title="Anmeldung hinzufügen">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="label">Helfer</label>
          <select v-model="form.volunteer_id" class="input" required>
            <option value="">Bitte wählen</option>
            <option v-for="v in volunteers" :key="v.id" :value="v.id">{{ v.name }}</option>
          </select>
        </div>
        <div>
          <label class="label">Schicht</label>
          <select v-model="form.shift_id" class="input" required>
            <option value="">Bitte wählen</option>
            <option v-for="s in shifts" :key="s.id" :value="s.id">
              {{ s.stand_name }} – {{ s.date_formatted }} {{ s.time_range }}
            </option>
          </select>
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
const registrations = ref([])
const volunteers = ref([])
const shifts = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const showModal = ref(false)
const form = ref({ volunteer_id: '', shift_id: '' })
const saveError = ref('')

onMounted(async () => {
  await Promise.all([load(), loadMeta()])
})

async function load() {
  const res = await adminApi.getRegistrations(route.params.slug, { page: page.value, per_page: 20 })
  registrations.value = res.data.data
  pages.value = res.data.pages
  total.value = res.data.total
}

async function loadMeta() {
  const [vRes, sRes] = await Promise.all([
    adminApi.getVolunteers(route.params.slug, { per_page: 500 }),
    adminApi.getShifts(route.params.slug, { per_page: 500 }),
  ])
  volunteers.value = vRes.data.data
  shifts.value = sRes.data.data
}

function openCreate() {
  form.value = { volunteer_id: '', shift_id: '' }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    await adminApi.createRegistration(route.params.slug, form.value)
    ui.success('Anmeldung eingetragen')
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteReg(r) {
  const ok = await ui.confirm({
    title: 'Anmeldung entfernen',
    message: `${r.volunteer_name} aus der Schicht entfernen?`,
    confirmText: 'Entfernen', danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteRegistration(route.params.slug, r.id)
    ui.success('Entfernt')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
