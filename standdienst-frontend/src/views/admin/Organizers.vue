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
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="name" @sort="toggleSort">Name</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="email" @sort="toggleSort">E-Mail</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="is_instance_admin" @sort="toggleSort">Rolle</SortTh>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Instanzen</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in sorted" :key="o.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3 font-medium text-gray-900">{{ o.name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ o.email }}</td>
            <td class="px-4 py-3">
              <span
                v-if="o.is_instance_admin"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700"
              >
                Instanz-Admin
              </span>
              <span v-else class="text-xs text-gray-400">Organisator</span>
            </td>
            <td class="px-4 py-3 text-gray-500">{{ o.instance_ids?.length ?? 0 }}</td>
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
        <div><label class="label">E-Mail</label><input v-model="form.email" type="email" class="input" required /></div>
        <div v-if="!editing">
          <label class="label">Passwort <span class="text-xs font-normal text-gray-400">(optional)</span></label>
          <input v-model="form.password" type="password" class="input" autocomplete="new-password" />
          <p class="text-xs text-gray-400 mt-1">
            Leer lassen → Einladungsmail mit Passwort-Einrichtungslink (7 Tage gültig)
          </p>
        </div>
        <div class="flex items-center gap-3">
          <input v-model="form.is_instance_admin" type="checkbox" id="is_instance_admin" class="rounded" />
          <label for="is_instance_admin" class="text-sm text-gray-700">
            Instanz-Admin
            <span class="text-xs text-gray-400 ml-1">(kann Einstellungen der eigenen Instanz bearbeiten)</span>
          </label>
        </div>

        <div>
          <label class="label">Zugeordnete Instanzen</label>
          <div v-if="!instances.length" class="text-xs text-gray-400 py-2">Keine Instanzen vorhanden</div>
          <div v-else class="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-48 overflow-y-auto">
            <label
              v-for="inst in instances"
              :key="inst.id"
              class="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer"
            >
              <input
                type="checkbox"
                :value="inst.id"
                v-model="form.instance_ids"
                class="rounded"
              />
              <span class="text-sm text-gray-700">{{ inst.name }}</span>
              <span class="text-xs text-gray-400 font-mono">{{ inst.slug }}</span>
            </label>
          </div>
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
import { useSort } from '@/composables/useSort'
import Modal from '@/components/Modal.vue'
import SortTh from '@/components/SortTh.vue'

const ui = useUiStore()
const organizers = ref([])
const instances = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ first_name: '', last_name: '', email: '', password: '', is_instance_admin: false, instance_ids: [] })
const saveError = ref('')

const { sortKey, sortDir, sorted, toggleSort } = useSort(organizers, 'name')

onMounted(async () => {
  await Promise.all([load(), loadInstances()])
})

async function load() {
  const res = await adminApi.getOrganizers({ per_page: 100 })
  organizers.value = res.data.data
}

async function loadInstances() {
  const res = await adminApi.getInstances({ per_page: 200 })
  instances.value = res.data.data
}

function openCreate() {
  editing.value = null
  form.value = { first_name: '', last_name: '', email: '', password: '', is_instance_admin: false, instance_ids: [] }
  saveError.value = ''
  showModal.value = true
}

function openEdit(o) {
  editing.value = o
  const parts = (o.name || '').split(' ')
  form.value = {
    first_name: o.first_name || parts[0] || '',
    last_name: o.last_name || parts.slice(1).join(' ') || '',
    email: o.email,
    is_instance_admin: o.is_instance_admin ?? false,
    instance_ids: [...(o.instance_ids ?? [])],
  }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateOrganizer(editing.value.id, {
        first_name: form.value.first_name,
        last_name: form.value.last_name,
        email: form.value.email,
        is_instance_admin: form.value.is_instance_admin,
        instance_ids: form.value.instance_ids,
      })
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
