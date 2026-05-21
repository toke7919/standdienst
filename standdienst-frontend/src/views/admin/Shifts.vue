<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Schichten</h1>
      <button class="btn-primary" @click="openCreate">Neue Schicht</button>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner size="lg" />
    </div>

    <template v-else>
      <!-- Eine Karte pro Datum, Stände als Untergruppe -->
      <div class="space-y-4">
        <div v-for="group in groupedShifts" :key="group.date" class="card overflow-hidden !p-0">
          <!-- Akzent-Streifen oben -->
          <div class="h-1 bg-primary-500 rounded-t-2xl" />

          <!-- Datum-Kopf -->
          <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <CalendarIcon class="w-5 h-5 text-primary-500 flex-shrink-0" />
              <h2 class="font-semibold text-gray-900">{{ group.date }}</h2>
            </div>
            <span class="text-xs text-gray-400 flex-shrink-0">
              {{ group.total }} {{ group.total === 1 ? 'Schicht' : 'Schichten' }}
            </span>
          </div>

          <!-- Stände als Untergruppen innerhalb des Datums -->
          <div>
            <template v-for="sg in group.standGroups" :key="sg.stand_name">
              <!-- Stand-Subheader -->
              <div class="px-5 py-1.5 bg-gray-50 border-b border-gray-100 flex items-center gap-2">
                <BuildingStorefrontIcon class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                <span class="text-xs font-semibold text-gray-500">{{ sg.stand_name }}</span>
              </div>
              <!-- Schicht-Zeilen -->
              <div
                v-for="s in sg.shifts"
                :key="s.id"
                class="flex items-center px-5 py-3 border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors duration-100"
              >
                <p class="text-sm font-medium text-gray-800 flex-1">{{ s.time_range }}</p>
                <div class="flex items-center gap-4">
                  <span :class="s.is_full ? 'badge-green' : 'badge-red'">
                    {{ s.current_count }}/{{ s.max_volunteers }}
                  </span>
                  <button class="text-xs text-gray-500 hover:text-gray-700 font-medium" @click="openDuplicate(s)">Duplizieren</button>
                  <button class="text-xs text-primary-600 hover:text-primary-800 font-medium" @click="openEdit(s)">Bearbeiten</button>
                  <button class="text-xs text-red-500 hover:text-red-700 font-medium" @click="deleteShift(s)">Löschen</button>
                </div>
              </div>
            </template>
          </div>
        </div>

        <div v-if="!groupedShifts.length" class="bg-white rounded-xl border border-gray-100 shadow-sm py-16 text-center">
          <ClockIcon class="w-10 h-10 text-gray-200 mx-auto mb-3" />
          <p class="text-gray-400 text-sm">Noch keine Schichten angelegt</p>
        </div>
      </div>

      <Pagination v-model:page="page" :pages="pages" :total="total" :per-page="perPage" @update:page="load" />
    </template>

    <Modal v-model="showModal" :title="editing ? 'Schicht bearbeiten' : 'Neue Schicht'">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="label">Stand</label>
          <select v-model="form.stand_id" class="input" required>
            <option value="">Bitte wählen</option>
            <option v-for="s in stands" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div>
          <label class="label">Datum</label>
          <select v-model="form.event_date_id" class="input" required>
            <option value="">Bitte wählen</option>
            <option v-for="d in dates" :key="d.id" :value="d.id">{{ d.formatted }}</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Von</label>
            <input v-model="form.start_time" type="time" class="input" required />
          </div>
          <div>
            <label class="label">Bis</label>
            <input v-model="form.end_time" type="time" class="input" required />
          </div>
        </div>
        <div>
          <label class="label">Max. Helfer</label>
          <input v-model.number="form.max_volunteers" type="number" min="1" class="input" required />
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
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import Modal from '@/components/Modal.vue'
import Pagination from '@/components/Pagination.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { CalendarIcon, BuildingStorefrontIcon, ClockIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const ui = useUiStore()
const shifts = ref([])
const stands = ref([])
const dates = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const perPage = 50
const loading = ref(true)

const showModal = ref(false)
const editing = ref(null)
const form = ref({ stand_id: '', event_date_id: '', start_time: '08:00', end_time: '12:00', max_volunteers: 2 })
const saveError = ref('')

// Primär nach Datum, sekundär nach Stand-Sortierung, tertiär nach Uhrzeit
const standOrderMap = computed(() => {
  const map = {}
  stands.value.forEach(s => { map[s.id] = s.sort_order ?? 0 })
  return map
})

const groupedShifts = computed(() => {
  const sorted = [...shifts.value].sort((a, b) => {
    if (a.date_formatted !== b.date_formatted) return a.date_formatted.localeCompare(b.date_formatted, 'de')
    const orderDiff = (standOrderMap.value[a.stand_id] ?? 999) - (standOrderMap.value[b.stand_id] ?? 999)
    if (orderDiff !== 0) return orderDiff
    return (a.start_time || '').localeCompare(b.start_time || '')
  })
  const byDate = {}
  for (const s of sorted) {
    if (!byDate[s.date_formatted]) byDate[s.date_formatted] = {}
    if (!byDate[s.date_formatted][s.stand_name]) byDate[s.date_formatted][s.stand_name] = []
    byDate[s.date_formatted][s.stand_name].push(s)
  }
  return Object.entries(byDate).map(([date, standMap]) => ({
    date,
    standGroups: Object.entries(standMap).map(([stand_name, shifts]) => ({ stand_name, shifts })),
    total: Object.values(standMap).reduce((n, arr) => n + arr.length, 0),
  }))
})

onMounted(async () => {
  await Promise.all([load(), loadMeta()])
})

async function load() {
  loading.value = true
  try {
    const res = await adminApi.getShifts(route.params.slug, { page: page.value, per_page: perPage })
    shifts.value = res.data.data
    pages.value = res.data.pages
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  const [sRes, dRes] = await Promise.all([
    adminApi.getStands(route.params.slug),
    adminApi.getDates(route.params.slug),
  ])
  stands.value = sRes.data.data
  dates.value = dRes.data.data
}

function openCreate() {
  editing.value = null
  form.value = { stand_id: '', event_date_id: '', start_time: '08:00', end_time: '12:00', max_volunteers: 2 }
  saveError.value = ''
  showModal.value = true
}

function openEdit(s) {
  editing.value = s
  form.value = {
    stand_id: s.stand_id,
    event_date_id: s.event_date_id,
    start_time: (s.start_time || '').substring(0, 5),
    end_time: (s.end_time || '').substring(0, 5),
    max_volunteers: s.max_volunteers,
  }
  saveError.value = ''
  showModal.value = true
}

function openDuplicate(s) {
  editing.value = null
  form.value = {
    stand_id: s.stand_id,
    event_date_id: s.event_date_id,
    start_time: (s.start_time || '').substring(0, 5),
    end_time: (s.end_time || '').substring(0, 5),
    max_volunteers: s.max_volunteers,
  }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateShift(route.params.slug, editing.value.id, {
        start_time: form.value.start_time,
        end_time: form.value.end_time,
        max_volunteers: form.value.max_volunteers,
      })
      ui.success('Schicht aktualisiert')
    } else {
      await adminApi.createShift(route.params.slug, form.value)
      ui.success('Schicht erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteShift(s) {
  const ok = await ui.confirm({
    title: 'Schicht löschen', message: 'Schicht und alle Anmeldungen löschen?',
    confirmText: 'Löschen', danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteShift(route.params.slug, s.id)
    ui.success('Gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
