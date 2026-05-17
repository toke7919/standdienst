<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Organisatoren</h1>
      <button class="btn-primary" @click="openCreate">Neuer Organisator</button>
    </div>

    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Name</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">E-Mail</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Instanzen</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in organizers" :key="o.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3 font-medium text-gray-900">{{ o.name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ o.email }}</td>
            <td class="px-4 py-3 text-gray-500">{{ o.instance_count ?? 0 }}</td>
            <td class="px-4 py-3 text-right space-x-2">
              <button class="text-xs text-primary-600 hover:underline" @click="openEdit(o)">Bearbeiten</button>
              <button class="text-xs text-red-600 hover:underline" @click="deleteOrg(o)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" :title="editing ? 'Organisator bearbeiten' : 'Neuer Organisator'">
      <form @submit.prevent="save" class="space-y-4">
        <div><label class="label">Name</label><input v-model="form.name" class="input" required /></div>
        <div><label class="label">E-Mail</label><input v-model="form.email" type="email" class="input" required /></div>
        <div v-if="!editing">
          <label class="label">Passwort</label>
          <input v-model="form.password" type="password" class="input" required />
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
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import Modal from '@/components/Modal.vue'

const ui = useUiStore()
const organizers = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ name: '', email: '', password: '' })
const saveError = ref('')

onMounted(load)

async function load() {
  const res = await adminApi.getOrganizers({ per_page: 100 })
  organizers.value = res.data.data
}

function openCreate() {
  editing.value = null
  form.value = { name: '', email: '', password: '' }
  saveError.value = ''
  showModal.value = true
}

function openEdit(o) {
  editing.value = o
  form.value = { name: o.name, email: o.email }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateOrganizer(editing.value.id, form.value)
      ui.success('Organisator aktualisiert')
    } else {
      await adminApi.createOrganizer(form.value)
      ui.success('Organisator erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteOrg(o) {
  const ok = await ui.confirm({
    title: 'Löschen', message: `${o.name} löschen?`, confirmText: 'Löschen', danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteOrganizer(o.id)
    ui.success('Gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
