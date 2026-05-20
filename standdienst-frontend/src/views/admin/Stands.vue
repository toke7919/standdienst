<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Stände</h1>
      <button class="btn-primary" @click="openCreate">Neuer Stand</button>
    </div>

    <div class="space-y-2">
      <div
        v-for="stand in stands"
        :key="stand.id"
        class="group bg-white rounded-xl border border-gray-100 shadow-sm px-5 py-4 flex items-center gap-4 hover:border-primary-200 transition-colors duration-150"
      >
        <div class="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
          <BuildingStorefrontIcon class="w-5 h-5 text-primary-600" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-gray-900">{{ stand.name }}</p>
          <p v-if="stand.description" class="text-sm text-gray-500 mt-0.5 truncate">{{ stand.description }}</p>
        </div>
        <div class="flex items-center gap-3">
          <button class="text-sm text-primary-600 hover:text-primary-800 font-medium" @click="openEdit(stand)">Bearbeiten</button>
          <span class="text-gray-200">|</span>
          <button class="text-sm text-red-500 hover:text-red-700 font-medium" @click="deleteStand(stand)">Löschen</button>
        </div>
      </div>

      <div v-if="!stands.length" class="bg-white rounded-xl border border-gray-100 shadow-sm py-16 text-center">
        <BuildingStorefrontIcon class="w-10 h-10 text-gray-200 mx-auto mb-3" />
        <p class="text-gray-400 text-sm">Noch keine Stände angelegt</p>
      </div>
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
import { BuildingStorefrontIcon } from '@heroicons/vue/24/outline'

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
