<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-ink">Stände</h1>
      <button class="btn-primary" @click="openCreate">Neuer Stand</button>
    </div>

    <div class="space-y-2">
      <div
        v-for="(stand, idx) in stands"
        :key="stand.id"
        draggable="true"
        @dragstart="onDragStart(idx)"
        @dragover.prevent="onDragOver(idx)"
        @drop.prevent="onDrop"
        @dragend="onDragEnd"
        class="group bg-soft rounded-md border border-sand shadow-sm px-5 py-4 flex items-center gap-4 hover:border-primary-200 transition-colors duration-150"
        :class="dragOver === idx ? 'border-primary-400 bg-primary-50/50' : ''"
      >
        <div class="cursor-grab active:cursor-grabbing text-sand hover:text-muted flex-shrink-0 touch-none" title="Ziehen zum Sortieren">
          <Bars3Icon class="w-5 h-5" />
        </div>
        <div class="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
          <BuildingStorefrontIcon class="w-5 h-5 text-primary-600" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-ink truncate">{{ stand.name }}</p>
          <p v-if="stand.description" class="text-sm text-muted mt-0.5 truncate">{{ stand.description }}</p>
        </div>
        <div class="flex items-center gap-3 flex-shrink-0">
          <button class="text-sm text-primary-600 hover:text-primary-800 font-medium" @click="openEdit(stand)">Bearbeiten</button>
          <span class="text-sand">|</span>
          <button class="text-sm text-red-500 hover:text-red-700 font-medium" @click="deleteStand(stand)">Löschen</button>
        </div>
      </div>

      <div v-if="!stands.length" class="bg-soft rounded-md border border-sand shadow-sm py-16 text-center">
        <BuildingStorefrontIcon class="w-10 h-10 text-sand mx-auto mb-3" />
        <p class="text-muted text-sm">Noch keine Stände angelegt</p>
      </div>
    </div>

    <Modal v-model="showModal" :title="editing ? 'Stand bearbeiten' : 'Neuer Stand'">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="label">Name</label>
          <input v-model="form.name" class="input" required />
        </div>
        <div>
          <label class="label">Beschreibung <span class="font-normal text-muted text-xs">(optional)</span></label>
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
import { BuildingStorefrontIcon, Bars3Icon } from '@heroicons/vue/24/outline'

const route = useRoute()
const ui = useUiStore()
const stands = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ name: '', description: '' })
const saveError = ref('')

// Drag-and-drop state
const dragIdx = ref(null)
const dragOver = ref(null)

onMounted(load)

async function load() {
  const res = await adminApi.getStands(route.params.slug)
  stands.value = res.data.data
}

function onDragStart(idx) {
  dragIdx.value = idx
}

function onDragOver(idx) {
  dragOver.value = idx
}

function onDrop() {
  if (dragIdx.value === null || dragOver.value === null || dragIdx.value === dragOver.value) return
  const arr = [...stands.value]
  const [moved] = arr.splice(dragIdx.value, 1)
  arr.splice(dragOver.value, 0, moved)
  stands.value = arr
  saveOrder()
}

function onDragEnd() {
  dragIdx.value = null
  dragOver.value = null
}

async function saveOrder() {
  try {
    await adminApi.reorderStands(route.params.slug, stands.value.map(s => s.id))
  } catch {
    ui.err('Reihenfolge konnte nicht gespeichert werden')
    await load()
  }
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
      await adminApi.updateStand(route.params.slug, editing.value.id, {
        ...form.value,
        updated_at: editing.value.updated_at,
      })
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
    message: `"${s.name}" löschen? Alle Dienste werden ebenfalls gelöscht.`,
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
