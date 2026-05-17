<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Stände</h1>
      <button class="btn-primary" @click="openCreate">Neuer Stand</button>
    </div>

    <div class="card space-y-2">
      <div
        v-for="stand in stands"
        :key="stand.id"
        class="flex items-center justify-between p-3 rounded-lg border border-gray-100 bg-gray-50"
      >
        <div>
          <p class="font-medium text-gray-900">{{ stand.name }}</p>
          <p v-if="stand.description" class="text-xs text-gray-500 mt-0.5">{{ stand.description }}</p>
        </div>
        <div class="flex gap-2">
          <button class="text-xs text-primary-600 hover:underline" @click="openEdit(stand)">Bearbeiten</button>
          <button class="text-xs text-red-600 hover:underline" @click="deleteStand(stand)">Löschen</button>
        </div>
      </div>
      <p v-if="!stands.length" class="text-center text-gray-400 py-8">Noch keine Stände</p>
    </div>

    <Modal v-model="showModal" :title="editing ? 'Stand bearbeiten' : 'Neuer Stand'">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="label">Name</label>
          <input v-model="form.name" class="input" required />
        </div>
        <div>
          <label class="label">Beschreibung</label>
          <input v-model="form.description" class="input" />
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
const stands = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ name: '', description: '' })
const saveError = ref('')

onMounted(load)

async function load() {
  const res = await adminApi.getStands(route.params.slug)
  stands.value = res.data.data
}

function openCreate() {
  editing.value = null
  form.value = { name: '', description: '' }
  saveError.value = ''
  showModal.value = true
}

function openEdit(s) {
  editing.value = s
  form.value = { name: s.name, description: s.description || '' }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateStand(route.params.slug, editing.value.id, form.value)
      ui.success('Stand aktualisiert')
    } else {
      await adminApi.createStand(route.params.slug, form.value)
      ui.success('Stand erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteStand(s) {
  const ok = await ui.confirm({
    title: 'Stand löschen',
    message: `"${s.name}" löschen? Alle Schichten werden ebenfalls gelöscht.`,
    confirmText: 'Löschen', danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteStand(route.params.slug, s.id)
    ui.success('Gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
