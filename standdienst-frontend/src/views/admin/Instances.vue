<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Instanzen</h1>
      <button class="btn-primary" @click="openCreate">Neue Instanz</button>
    </div>

    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Name</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Slug</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Status</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="inst in instances" :key="inst.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3 font-medium text-gray-900">{{ inst.name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ inst.slug }}</td>
            <td class="px-4 py-3">
              <span :class="inst.is_active ? 'badge-green' : 'badge-red'">
                {{ inst.is_active ? 'Aktiv' : 'Inaktiv' }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <button class="text-xs text-primary-600 hover:underline mr-3" @click="openEdit(inst)">
                Bearbeiten
              </button>
              <button class="text-xs text-red-600 hover:underline" @click="deleteInst(inst)">
                Löschen
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" :title="editing ? 'Instanz bearbeiten' : 'Neue Instanz'">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="label">Name</label>
          <input v-model="form.name" class="input" required />
        </div>
        <div>
          <label class="label">Slug (URL-Kürzel)</label>
          <input v-model="form.slug" class="input" required :disabled="!!editing" />
        </div>
        <div class="flex items-center gap-2">
          <input v-model="form.is_active" type="checkbox" id="active" class="rounded" />
          <label for="active" class="text-sm text-gray-700">Aktiv</label>
        </div>
        <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
        <div class="flex gap-3 justify-end pt-2">
          <button type="button" class="btn-secondary" @click="showModal = false">Abbrechen</button>
          <button type="submit" class="btn-primary" :disabled="saving">Speichern</button>
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
const instances = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ name: '', slug: '', is_active: true })
const saving = ref(false)
const saveError = ref('')

onMounted(load)

async function load() {
  const res = await adminApi.getInstances({ per_page: 100 })
  instances.value = res.data.data
}

function openCreate() {
  editing.value = null
  form.value = { name: '', slug: '', is_active: true }
  saveError.value = ''
  showModal.value = true
}

function openEdit(inst) {
  editing.value = inst
  form.value = { name: inst.name, slug: inst.slug, is_active: inst.is_active }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateInstance(editing.value.id, form.value)
      ui.success('Instanz aktualisiert')
    } else {
      await adminApi.createInstance(form.value)
      ui.success('Instanz erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}

async function deleteInst(inst) {
  const ok = await ui.confirm({
    title: 'Instanz löschen',
    message: `"${inst.name}" wirklich löschen? Alle Daten gehen verloren!`,
    confirmText: 'Löschen',
    danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteInstance(inst.id)
    ui.success('Instanz gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler beim Löschen')
  }
}
</script>
