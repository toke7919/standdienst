<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Essensspenden</h1>

    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-800">Kategorien</h2>
      <button class="btn-secondary text-sm" @click="openCreateType">Neue Kategorie</button>
    </div>

    <div class="card mb-8 space-y-2">
      <div v-for="t in foodTypes" :key="t.id" class="flex items-center justify-between p-3 rounded-lg border border-gray-100 bg-gray-50">
        <div>
          <p class="font-medium text-gray-900">{{ t.name }}</p>
          <p class="text-xs text-gray-500">Max: {{ t.max_quantity }} | Kühlung: {{ t.needs_refrigeration ? 'Ja' : 'Nein' }}</p>
        </div>
        <div class="flex gap-2">
          <button class="text-xs text-primary-600 hover:underline" @click="openEditType(t)">Bearbeiten</button>
          <button class="text-xs text-red-600 hover:underline" @click="deleteType(t)">Löschen</button>
        </div>
      </div>
      <p v-if="!foodTypes.length" class="text-center text-gray-400 py-4">Noch keine Kategorien</p>
    </div>

    <h2 class="text-lg font-semibold text-gray-800 mb-4">Angemeldete Spenden</h2>
    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Helfer</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Kategorie</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Menge</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in donations" :key="d.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3">{{ d.volunteer_name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ d.food_type_name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ d.quantity }}</td>
            <td class="px-4 py-3 text-right">
              <button class="text-xs text-red-600 hover:underline" @click="deleteDonation(d)">Entfernen</button>
            </td>
          </tr>
          <tr v-if="!donations.length">
            <td colspan="4" class="px-4 py-8 text-center text-gray-400">Keine Spenden</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showTypeModal" :title="editingType ? 'Kategorie bearbeiten' : 'Neue Kategorie'">
      <form @submit.prevent="saveType" class="space-y-4">
        <div><label class="label">Name</label><input v-model="typeForm.name" class="input" required /></div>
        <div><label class="label">Max. Menge</label><input v-model.number="typeForm.max_quantity" type="number" min="1" class="input" /></div>
        <div class="flex items-center gap-2">
          <input v-model="typeForm.needs_refrigeration" type="checkbox" id="fridge" />
          <label for="fridge" class="text-sm text-gray-700">Kühlung erforderlich</label>
        </div>
        <p v-if="typeError" class="text-sm text-red-600">{{ typeError }}</p>
        <div class="flex gap-3 justify-end pt-2">
          <button type="button" class="btn-secondary" @click="showTypeModal = false">Abbrechen</button>
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
const foodTypes = ref([])
const donations = ref([])
const showTypeModal = ref(false)
const editingType = ref(null)
const typeForm = ref({ name: '', max_quantity: 10, needs_refrigeration: false })
const typeError = ref('')

onMounted(load)

async function load() {
  const [tRes, dRes] = await Promise.all([
    adminApi.getFoodTypes(route.params.slug),
    adminApi.getFoodDonations(route.params.slug, { per_page: 200 }),
  ])
  foodTypes.value = tRes.data.data
  donations.value = dRes.data.data
}

function openCreateType() {
  editingType.value = null
  typeForm.value = { name: '', max_quantity: 10, needs_refrigeration: false }
  typeError.value = ''
  showTypeModal.value = true
}

function openEditType(t) {
  editingType.value = t
  typeForm.value = { name: t.name, max_quantity: t.max_quantity, needs_refrigeration: t.needs_refrigeration }
  typeError.value = ''
  showTypeModal.value = true
}

async function saveType() {
  typeError.value = ''
  try {
    if (editingType.value) {
      await adminApi.updateFoodType(route.params.slug, editingType.value.id, typeForm.value)
      ui.success('Aktualisiert')
    } else {
      await adminApi.createFoodType(route.params.slug, typeForm.value)
      ui.success('Erstellt')
    }
    showTypeModal.value = false
    await load()
  } catch (e) {
    typeError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteType(t) {
  const ok = await ui.confirm({ title: 'Löschen', message: `"${t.name}" löschen?`, danger: true })
  if (!ok) return
  try { await adminApi.deleteFoodType(route.params.slug, t.id); await load() }
  catch (e) { ui.err(e.response?.data?.error || 'Fehler') }
}

async function deleteDonation(d) {
  const ok = await ui.confirm({ title: 'Spende entfernen', message: 'Spende entfernen?', danger: true })
  if (!ok) return
  try { await adminApi.deleteFoodDonation(route.params.slug, d.id); await load() }
  catch (e) { ui.err(e.response?.data?.error || 'Fehler') }
}
</script>
