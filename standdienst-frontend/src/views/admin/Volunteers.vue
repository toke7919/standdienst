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
            <SortTh :sort-key="localSortKey" :sort-dir="localSortDir" field="name" @sort="toggleLocalSort">Name</SortTh>
            <SortTh :sort-key="localSortKey" :sort-dir="localSortDir" field="email" @sort="toggleLocalSort">E-Mail</SortTh>
            <SortTh :sort-key="localSortKey" :sort-dir="localSortDir" field="created_at" @sort="toggleLocalSort">Angemeldet</SortTh>
            <SortTh :sort-key="localSortKey" :sort-dir="localSortDir" field="shift_count" @sort="toggleLocalSort" class="text-right">Schichten</SortTh>
            <SortTh :sort-key="localSortKey" :sort-dir="localSortDir" field="food_count" @sort="toggleLocalSort" class="text-right">Spenden</SortTh>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in sortedVolunteers" :key="v.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3 font-medium text-gray-900">{{ v.display_name || v.name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ v.email || '—' }}</td>
            <td class="px-4 py-3 text-gray-500 whitespace-nowrap">{{ formatDate(v.created_at) }}</td>
            <td class="px-4 py-3 text-right text-gray-600 tabular-nums">{{ v.shift_count ?? 0 }}</td>
            <td class="px-4 py-3 text-right text-gray-600 tabular-nums">{{ v.food_count ?? 0 }}</td>
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
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Vorname</label>
            <input v-model="form.first_name" class="input" required />
          </div>
          <div>
            <label class="label">Nachname</label>
            <input v-model="form.last_name" class="input" />
          </div>
        </div>
        <div>
          <label class="label">E-Mail</label>
          <input v-model="form.email" type="email" class="input" />
        </div>
        <div v-if="!editing">
          <label class="label">Passwort</label>
          <input v-model="form.password" type="password" class="input" placeholder="Leer lassen = Willkommens-E-Mail" />
          <p v-if="form.email && !form.password" class="text-xs text-gray-500 mt-1">
            Helfer erhält eine Willkommens-E-Mail zum Einrichten des Passworts.
          </p>
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
import { useSort } from '@/composables/useSort'
import Modal from '@/components/Modal.vue'
import Pagination from '@/components/Pagination.vue'
import SortTh from '@/components/SortTh.vue'

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
const { sortKey: localSortKey, sortDir: localSortDir, sorted: sortedVolunteers, toggleSort: toggleLocalSort } = useSort(volunteers, 'name')
const form = ref({ first_name: '', last_name: '', email: '', password: '' })
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
  return iso ? new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }) : ''
}

function openCreate() {
  editing.value = null
  form.value = { first_name: '', last_name: '', email: '', password: '' }
  saveError.value = ''
  showModal.value = true
}

function openEdit(v) {
  editing.value = v
  form.value = {
    first_name: v.first_name || v.name || '',
    last_name: v.last_name || '',
    email: v.email || '',
  }
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
