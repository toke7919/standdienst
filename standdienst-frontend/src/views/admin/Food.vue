<template>
  <div>
    <h1 class="text-2xl font-bold text-ink mb-6">Essensspenden</h1>

    <!-- ── Kategorien ──────────────────────────────────────────────── -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-ink">Kategorien</h2>
      <button class="btn-secondary text-sm" @click="openCreateType">Neue Kategorie</button>
    </div>

    <div class="card mb-8 space-y-2">
      <div v-for="t in foodTypes" :key="t.id" class="flex items-center justify-between p-3 rounded-lg border border-sand bg-bg-brand">
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <p class="font-medium text-ink">{{ t.name }}</p>
            <span v-if="t.event_date_formatted" class="text-sm text-muted">{{ t.event_date_formatted }}</span>
          </div>
          <p v-if="t.delivery_datetime || t.delivery_location" class="text-xs text-muted">
            <span v-if="t.delivery_datetime">Abgabe: {{ fmtDt(t.delivery_datetime) }}</span>
            <span v-if="t.delivery_location"> · {{ t.delivery_location }}</span>
          </p>
        </div>
        <div class="flex gap-2">
          <button class="text-xs text-primary-600 hover:underline" @click="openEditType(t)">Bearbeiten</button>
          <button class="text-xs text-red-600 hover:underline" @click="deleteType(t)">Löschen</button>
        </div>
      </div>
      <p v-if="!foodTypes.length" class="text-center text-muted py-4">Noch keine Kategorien</p>
    </div>

    <!-- ── Angemeldete Spenden je Kategorie ───────────────────────── -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-ink">Angemeldete Spenden</h2>
      <button class="btn-secondary text-sm" @click="openCreateDonation(null)">Spende eintragen</button>
    </div>

    <div v-if="!foodTypes.length" class="card p-6 text-center text-muted">Noch keine Kategorien angelegt.</div>

    <div v-else class="space-y-6">
      <div v-for="t in foodTypes" :key="`don-${t.id}`">
        <div class="card overflow-hidden p-0!">
          <div class="h-1 bg-primary-500 rounded-t-md" />
          <div class="px-5 py-4 border-b border-sand flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <CalendarIcon class="w-5 h-5 text-primary-500 shrink-0" />
              <div>
                <div class="flex items-center gap-2 flex-wrap">
                  <p class="font-semibold text-ink text-sm">{{ t.name }}</p>
                  <span v-if="t.event_date_formatted" class="text-sm text-muted">{{ t.event_date_formatted }}</span>
                </div>
                <p v-if="t.delivery_datetime" class="text-xs text-muted mt-0.5">
                  Abgabe: {{ fmtDt(t.delivery_datetime) }}
                </p>
              </div>
            </div>
            <span class="text-xs text-muted shrink-0">{{ donationsByType(t.id).length }} Spende{{ donationsByType(t.id).length !== 1 ? 'n' : '' }}</span>
          </div>
          <!-- Mobile: gestapelte Liste -->
          <div class="md:hidden divide-y divide-sand">
            <div v-for="d in donationsByType(t.id)" :key="d.id" class="flex items-start gap-3 px-4 py-3">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span class="font-medium text-ink text-sm">{{ d.volunteer_name }}</span>
                  <span
                    v-if="d.by_admin"
                    class="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full bg-bg-brand text-muted border border-sand"
                    title="Durch Admin/Organisator eingetragen"
                  >
                    <PencilSquareIcon class="w-2.5 h-2.5" />
                    Admin
                  </span>
                </div>
                <p v-if="d.description" class="text-xs text-muted mt-0.5">{{ d.description }}</p>
                <span v-if="d.needs_refrigeration" class="badge-blue mt-1 inline-flex">Kühlung</span>
              </div>
              <div class="flex flex-col items-end gap-1.5 shrink-0">
                <button class="text-xs text-primary-600 hover:underline" @click="openEditDonation(d)">Bearbeiten</button>
                <button class="text-xs text-red-600 hover:underline" @click="deleteDonation(d)">Entfernen</button>
              </div>
            </div>
            <div v-if="!donationsByType(t.id).length" class="px-4 py-5 text-center text-muted text-xs">Keine Spenden</div>
          </div>

          <!-- Desktop: Tabelle -->
          <table class="hidden md:table w-full text-sm">
            <thead class="bg-bg-brand border-b border-sand">
              <tr>
                <th class="px-4 py-2.5 text-left font-medium text-muted">Name</th>
                <th class="px-4 py-2.5 text-left font-medium text-muted">Beschreibung</th>
                <th class="px-4 py-2.5 text-left font-medium text-muted">Kühlung</th>
                <th class="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in donationsByType(t.id)" :key="d.id" class="border-b border-sand hover:bg-bg-warm">
                <td class="px-4 py-3">
                  <span class="inline-flex items-center gap-1.5">
                    {{ d.volunteer_name }}
                    <span
                      v-if="d.by_admin"
                      class="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full bg-bg-brand text-muted border border-sand"
                      title="Durch Admin/Organisator eingetragen"
                    >
                      <PencilSquareIcon class="w-2.5 h-2.5" />
                      Admin
                    </span>
                  </span>
                </td>
                <td class="px-4 py-3 text-muted">{{ d.description }}</td>
                <td class="px-4 py-3">
                  <span v-if="d.needs_refrigeration" class="badge-blue">Kühlung</span>
                </td>
                <td class="px-4 py-3 text-right">
                  <div class="flex items-center justify-end gap-3">
                    <button class="text-xs text-primary-600 hover:underline" @click="openEditDonation(d)">Bearbeiten</button>
                    <button class="text-xs text-red-600 hover:underline" @click="deleteDonation(d)">Entfernen</button>
                  </div>
                </td>
              </tr>
              <tr v-if="!donationsByType(t.id).length">
                <td colspan="4" class="px-4 py-5 text-center text-muted text-xs">Keine Spenden</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Modal: Spende eintragen / bearbeiten ───────────────────── -->
    <Modal v-model="showDonationModal" :title="editingDonation ? 'Spende bearbeiten' : 'Spende eintragen'">
      <form @submit.prevent="saveDonation" class="space-y-4">
        <div v-if="!editingDonation">
          <label class="label">Name des Spenders</label>
          <input v-model="donationForm.guest_name" class="input" required maxlength="100" />
        </div>
        <div v-if="!editingDonation">
          <label class="label">Kategorie</label>
          <select v-model.number="donationForm.food_type_id" class="input" required @change="onTypeChange">
            <option value="">Kategorie wählen …</option>
            <option v-for="t in foodTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>
        <div>
          <label class="label">Beschreibung</label>
          <input v-model="donationForm.description" class="input" required maxlength="100" />
        </div>
        <div v-if="editingDonation || selectedTypeRefrigeration" class="flex items-center gap-2">
          <input v-model="donationForm.needs_refrigeration" type="checkbox" id="don-refrig" />
          <label for="don-refrig" class="text-sm text-ink/80">Kühlung erforderlich</label>
        </div>
        <p v-if="donationError" class="text-sm text-red-600">{{ donationError }}</p>
        <div class="flex gap-3 justify-end pt-2">
          <button type="button" class="btn-secondary" @click="showDonationModal = false">Abbrechen</button>
          <button type="submit" class="btn-primary">Speichern</button>
        </div>
      </form>
    </Modal>

    <!-- ── Modal: Kategorie anlegen / bearbeiten ──────────────────── -->
    <Modal v-model="showTypeModal" :title="editingType ? 'Kategorie bearbeiten' : 'Neue Kategorie'">
      <form @submit.prevent="saveType" class="space-y-4">
        <div v-if="!editingType">
          <label class="label">Termin</label>
          <select v-model.number="typeForm.event_date_id" class="input" required>
            <option value="">Termin wählen …</option>
            <option v-for="d in eventDates" :key="d.id" :value="d.id">{{ d.formatted }}</option>
          </select>
        </div>
        <div><label class="label">Name</label><input v-model="typeForm.name" class="input" placeholder="z.B. Kuchen" required /></div>
        <div>
          <label class="label">Abgabezeitpunkt</label>
          <input v-model="typeForm.delivery_datetime" type="datetime-local" class="input" required />
        </div>
        <div>
          <label class="label">Abgabeort</label>
          <input v-model="typeForm.delivery_location" class="input" placeholder="z.B. Festplatz" maxlength="200" required />
        </div>
        <div>
          <label class="label">Hinweise <span class="font-normal text-muted text-xs">(optional)</span></label>
          <textarea v-model="typeForm.notes" class="input" rows="2" />
        </div>
        <div class="flex items-center gap-2">
          <input v-model="typeForm.refrigeration_enabled" type="checkbox" id="refrig" />
          <label for="refrig" class="text-sm text-ink/80">Kühlung-Option für Helfer anzeigen</label>
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
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import Modal from '@/components/Modal.vue'
import { CalendarIcon, PencilSquareIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const ui = useUiStore()
const foodTypes = ref([])
const donations = ref([])
const eventDates = ref([])

const showTypeModal = ref(false)
const editingType = ref(null)
const typeForm = ref({ event_date_id: '', name: '', delivery_datetime: '', delivery_location: '', notes: '', refrigeration_enabled: false })
const typeError = ref('')

const showDonationModal = ref(false)
const editingDonation = ref(null)
const donationForm = ref({ guest_name: '', food_type_id: '', description: '', needs_refrigeration: false })
const donationError = ref('')

const selectedTypeRefrigeration = computed(() => {
  const t = foodTypes.value.find(t => t.id === donationForm.value.food_type_id)
  return t?.refrigeration_enabled ?? false
})

function donationsByType(typeId) {
  return donations.value.filter(d => d.food_type_id === typeId)
}

onMounted(load)

async function load() {
  const [tRes, dRes, dateRes] = await Promise.all([
    adminApi.getFoodTypes(route.params.slug),
    adminApi.getFoodDonations(route.params.slug, { per_page: 500 }),
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
      await adminApi.updateFoodType(route.params.slug, editingType.value.id, {
        ...payload,
        updated_at: editingType.value.updated_at,
      })
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

function openCreateDonation(typeId) {
  editingDonation.value = null
  donationForm.value = { guest_name: '', food_type_id: typeId || '', description: '', needs_refrigeration: false }
  donationError.value = ''
  showDonationModal.value = true
}

function openEditDonation(d) {
  editingDonation.value = d
  donationForm.value = {
    guest_name: d.volunteer_name,
    food_type_id: d.food_type_id,
    description: d.description || '',
    needs_refrigeration: d.needs_refrigeration ?? false,
  }
  donationError.value = ''
  showDonationModal.value = true
}

function onTypeChange() {
  donationForm.value.needs_refrigeration = false
}

async function saveDonation() {
  donationError.value = ''
  try {
    if (editingDonation.value) {
      await adminApi.updateFoodDonation(route.params.slug, editingDonation.value.id, {
        description: donationForm.value.description,
        needs_refrigeration: donationForm.value.needs_refrigeration,
      })
      ui.success('Spende aktualisiert')
    } else {
      await adminApi.createFoodDonation(route.params.slug, {
        guest_name: donationForm.value.guest_name,
        food_type_id: donationForm.value.food_type_id,
        description: donationForm.value.description,
        needs_refrigeration: donationForm.value.needs_refrigeration,
      })
      ui.success('Spende eingetragen')
    }
    showDonationModal.value = false
    await load()
  } catch (e) {
    donationError.value = e.response?.data?.error || 'Fehler'
  }
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
