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
          <p class="text-xs text-gray-500">
            {{ t.event_date_label || '' }}
            <span v-if="t.delivery_datetime"> · Lieferung: {{ fmtDt(t.delivery_datetime) }}</span>
            <span v-if="t.delivery_location"> · {{ t.delivery_location }}</span>
          </p>
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
            <th class="px-4 py-3 text-left font-medium text-gray-500">Beschreibung</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Kühlung</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in donations" :key="d.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3">{{ d.volunteer_name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ d.food_type_name }}</td>
            <td class="px-4 py-3 text-gray-500">{{ d.description }}</td>
            <td class="px-4 py-3">
              <span v-if="d.needs_refrigeration" class="badge-blue">Kühlung</span>
            </td>
            <td class="px-4 py-3 text-right">
              <button class="text-xs text-red-600 hover:underline" @click="deleteDonation(d)">Entfernen</button>
            </td>
          </tr>
          <tr v-if="!donations.length">
            <td colspan="5" class="px-4 py-8 text-center text-gray-400">Keine Spenden</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showTypeModal" :title="editingType ? 'Kategorie bearbeiten' : 'Neue Kategorie'">
      <form @submit.prevent="saveType" class="space-y-4">
        <div v-if="!editingType">
          <label class="label">Termin</label>
          <select v-model.number="typeForm.event_date_id" class="input" required>
            <option value="">Termin wählen …</option>
            <option v-for="d in eventDates" :key="d.id" :value="d.id">{{ d.formatted }}</option>
          </select>
        </div>
        <div><label class="label">Name</label><input v-model="typeForm.name" class="input" required /></div>
        <div>
          <label class="label">Lieferzeitpunkt (optional)</label>
          <input v-model="typeForm.delivery_datetime" type="datetime-local" class="input" />
        </div>
        <div>
          <label class="label">Lieferort (optional)</label>
          <input v-model="typeForm.delivery_location" class="input" maxlength="200" />
        </div>
        <div>
          <label class="label">Hinweise (optional)</label>
          <textarea v-model="typeForm.notes" class="input" rows="2" />
        </div>
        <div class="flex items-center gap-2">
          <input v-model="typeForm.refrigeration_enabled" type="checkbox" id="refrig" />
          <label for="refrig" class="text-sm text-gray-700">Kühlung-Option für Helfer anzeigen</label>
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
const eventDates = ref([])
const showTypeModal = ref(false)
const editingType = ref(null)
const typeForm = ref({ event_date_id: '', name: '', delivery_datetime: '', delivery_location: '', notes: '', refrigeration_enabled: false })
const typeError = ref('')

onMounted(load)

async function load() {
  const [tRes, dRes, dateRes] = await Promise.all([
    adminApi.getFoodTypes(route.params.slug),
    adminApi.getFoodDonations(route.params.slug, { per_page: 200 }),
    adminApi.getDates(route.params.slug),
  ])
  foodTypes.value = tRes.data.data
  donations.value = dRes.data.data
  eventDates.value = dateRes.data.data
}

function openCreateType() {
  editingType.value = null
  typeForm.value = { event_date_id: '', name: '', delivery_datetime: '', delivery_location: '', notes: '', refrigeration_enabled: false }
  typeError.value = ''
  showTypeModal.value = true
}

function openEditType(t) {
  editingType.value = t
  typeForm.value = {
    name: t.name,
    delivery_datetime: t.delivery_datetime ? t.delivery_datetime.substring(0, 16) : '',
    delivery_location: t.delivery_location || '',
    notes: t.notes || '',
    refrigeration_enabled: t.refrigeration_enabled ?? false,
  }
  typeError.value = ''
  showTypeModal.value = true
}

async function saveType() {
  typeError.value = ''
  try {
    const payload = {
      name: typeForm.value.name,
      delivery_datetime: typeForm.value.delivery_datetime || null,
      delivery_location: typeForm.value.delivery_location || null,
      notes: typeForm.value.notes || null,
      refrigeration_enabled: typeForm.value.refrigeration_enabled,
    }
    if (editingType.value) {
      await adminApi.updateFoodType(route.params.slug, editingType.value.id, payload)
      ui.success('Aktualisiert')
    } else {
      await adminApi.createFoodType(route.params.slug, { ...payload, event_date_id: typeForm.value.event_date_id })
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

function fmtDt(iso) {
  return iso ? new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' }) : ''
}
</script>
