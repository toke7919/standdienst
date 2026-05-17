<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Helfer</h1>
      <button class="btn-primary" @click="openCreate">Neuer Helfer</button>
    </div>

    <div class="card mb-4 p-4">
      <input v-model="search" class="input max-w-sm" placeholder="Suchen…" />
    </div>

    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Name</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">E-Mail</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Angemeldet</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in volunteers" :key="v.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3 font-medium text-gray-900">{{ v.name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ v.email || '—' }}</td>
            <td class="px-4 py-3 text-gray-500">{{ formatDate(v.created_at) }}</td>
            <td class="px-4 py-3 text-right space-x-2">
              <button class="text-xs text-primary-600 hover:underline" @click="openEdit(v)">Bearbeiten</button>
              <button class="text-xs text-red-600 hover:underline" @click="deleteVol(v)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-model:page="page" :pages="pages" :total="total" :per-page="perPage" @update:page="load" />

    <Modal v-model="showModal" :title="editing ? 'Helfer bearbeiten' : 'Neuer Helfer'">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="label">Name</label>
          <input v-model="form.name" class="input" required />
        </div>
        <div>
          <label class="label">E-Mail</label>
          <input v-model="form.email" type="email" class="input" />
        </div>
        <div v-if="!editing">
          <label class="label">Passwort</label>
          <input v-model="form.password" type="password" class="input" />
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
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import Modal from '@/components/Modal.vue'
import Pagination from '@/components/Pagination.vue'

const route = useRoute()
const ui = useUiStore()

const volunteers = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const perPage = 20
const search = ref('')
const showModal = ref(false)
const editing = ref(null)
const form = ref({ name: '', email: '', password: '' })
const saveError = ref('')

onMounted(load)
watch(search, () => { page.value = 1; load() })

async function load() {
  const res = await adminApi.getVolunteers(route.params.slug, {
    page: page.value, per_page: perPage, search: search.value,
  })
  const d = res.data
  volunteers.value = d.data
  pages.value = d.pages
  total.value = d.total
}

function formatDate(iso) {
  return iso ? new Date(iso).toLocaleDateString('de-DE') : ''
}

function openCreate() {
  editing.value = null
  form.value = { name: '', email: '', password: '' }
  saveError.value = ''
  showModal.value = true
}

function openEdit(v) {
  editing.value = v
  form.value = { name: v.name, email: v.email || '' }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateVolunteer(route.params.slug, editing.value.id, form.value)
      ui.success('Helfer aktualisiert')
    } else {
      await adminApi.createVolunteer(route.params.slug, form.value)
      ui.success('Helfer erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteVol(v) {
  const ok = await ui.confirm({
    title: 'Helfer löschen',
    message: `${v.name} wirklich löschen?`,
    confirmText: 'Löschen',
    danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteVolunteer(route.params.slug, v.id)
    ui.success('Gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
