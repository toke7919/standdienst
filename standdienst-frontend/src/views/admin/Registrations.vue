<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-ink">Anmeldungen</h1>
      <button class="btn-primary" @click="openCreate(null)">Anmeldung hinzufügen</button>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner size="lg" />
    </div>

    <div v-else-if="!enrichedGrid.length" class="card p-6 text-center text-muted">
      Keine Dienste vorhanden.
    </div>

    <!-- Stundenplan: ein Block pro Datum – ein gemeinsamer Scroll-Container -->
    <div v-else class="overflow-x-auto">
    <div class="min-w-max space-y-8">
      <div v-for="section in enrichedGrid" :key="section.date_id">
        <!-- [overflow:clip] clippt Inhalte auf die Rundungen, ohne Scroll-Container zu erzeugen -->
        <div class="card [overflow:clip] !p-0">
          <div class="h-1 bg-primary-500 rounded-t-md" />
          <div class="px-5 py-4 border-b border-sand flex items-center gap-2.5">
            <CalendarIcon class="w-5 h-5 text-primary-500 flex-shrink-0" />
            <h2 class="font-semibold text-ink">{{ section.date_formatted }}</h2>
          </div>
          <!-- Stand-Spaltenheader -->
          <div class="flex border-b border-sand bg-bg-brand">
            <div class="w-14 flex-shrink-0 border-r border-sand" />
            <div class="flex flex-1" :style="`min-width: ${section.stands.length * MIN_COL_PX}px`">
              <div
                v-for="stand in section.stands"
                :key="stand.id"
                class="flex-1 px-3 py-3 text-sm font-semibold text-ink/80 border-r border-sand last:border-r-0 min-w-0 truncate"
                :style="`min-width: ${MIN_COL_PX}px`"
              >
                {{ stand.name }}
              </div>
            </div>
          </div>

          <!-- Timetable-Body -->
          <div class="flex">
            <!-- Zeitachse -->
            <div
              class="w-14 flex-shrink-0 relative border-r border-sand bg-bg-brand/50"
              :style="`height: ${section.gridHeight}px`"
            >
              <div
                v-for="h in section.hours"
                :key="h.label"
                class="absolute right-2 text-[10px] text-muted whitespace-nowrap"
                :style="`top: ${h.pct}%; transform: translateY(${h.ty}%)`"
              >{{ h.label }}</div>
            </div>

            <!-- Stand-Spalten -->
            <div
              class="flex flex-1"
              :style="`min-width: ${section.stands.length * MIN_COL_PX}px; height: ${section.gridHeight}px`"
            >
              <div
                v-for="({ stand, shiftItems }) in section.standShifts"
                :key="stand.id"
                class="relative flex-1 border-r border-sand last:border-r-0"
                :style="`min-width: ${MIN_COL_PX}px`"
              >
                <!-- Stunden-Rasterlinien -->
                <div
                  v-for="h in section.hours"
                  :key="h.label"
                  class="absolute inset-x-0 border-t border-sand/70"
                  :style="`top: ${h.pct}%`"
                />

                <!-- Dienst-Block -->
                <div
                  v-for="item in shiftItems"
                  :key="item.cell.shift_id"
                  class="absolute inset-x-1.5 rounded-xl border flex flex-col overflow-hidden"
                  :class="shiftBlockClass(item.cell)"
                  :style="`top: calc(${item.startPct}% + 2px); height: calc(${item.heightPct}% - 4px); min-height: 2.5rem`"
                >
                  <!-- Kopfzeile: Zeit + Badge -->
                  <div class="flex items-start justify-between gap-1 px-2 pt-2 flex-shrink-0">
                    <span class="text-[10px] font-semibold text-ink/80 leading-tight">{{ item.timeLabel }}</span>
                    <span
                      class="text-[9px] font-semibold px-1.5 py-0.5 rounded-full leading-tight flex-shrink-0"
                      :class="spotBadgeClass(item.cell)"
                    >
                      {{ item.cell.spots_left === 0 ? 'Voll' : `${item.cell.spots_left} frei` }}
                    </span>
                  </div>

                  <!-- Fortschrittsbalken -->
                  <div class="mx-2 mt-1 h-1 bg-white/60 rounded-full overflow-hidden flex-shrink-0">
                    <div
                      class="h-full rounded-full transition-all duration-300"
                      :class="fillBarClass(item.cell)"
                      :style="`width: ${fillPct(item.cell)}%`"
                    />
                  </div>

                  <!-- Angemeldete Namen -->
                  <div class="px-2 mt-1.5 flex flex-wrap gap-1 overflow-hidden min-h-0 flex-1 content-start">
                    <span
                      v-for="reg in item.cell.registrations"
                      :key="reg.id"
                      class="inline-flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded-full leading-tight"
                      :class="reg.by_admin
                        ? 'bg-white/80 text-ink/80 border border-sand'
                        : 'bg-primary-100 text-primary-700'"
                      :title="reg.by_admin ? 'Eingetragen durch Admin/Organisator' : 'Selbst angemeldet'"
                    >
                      <PencilSquareIcon v-if="reg.by_admin" class="w-2.5 h-2.5 flex-shrink-0 opacity-60" />
                      {{ reg.name }}
                      <button
                        type="button"
                        class="opacity-50 hover:opacity-100 ml-0.5 leading-none text-xs"
                        @click.stop="deleteReg(reg, item.cell.shift_id)"
                      >×</button>
                    </span>
                  </div>

                  <!-- Eintragen-Link -->
                  <button
                    v-if="item.cell.spots_left > 0"
                    type="button"
                    class="text-[10px] text-primary-600 hover:text-primary-800 font-medium px-2 pb-1.5 mt-auto text-left flex-shrink-0"
                    @click="openCreate(item.cell.shift_id)"
                  >+ Eintragen</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </div>

    <Modal v-model="showModal" title="Anmeldung hinzufügen">
      <form @submit.prevent="save" class="space-y-4">
        <!-- Mode toggle -->
        <div class="flex rounded-lg border border-sand overflow-hidden text-sm">
          <button
            type="button"
            class="flex-1 py-2 font-medium transition-colors"
            :class="mode === 'guest' ? 'bg-primary-600 text-white' : 'bg-soft text-muted hover:text-ink'"
            @click="mode = 'guest'"
          >Gast-Name</button>
          <button
            type="button"
            class="flex-1 py-2 font-medium transition-colors border-l border-sand"
            :class="mode === 'volunteer' ? 'bg-primary-600 text-white' : 'bg-soft text-muted hover:text-ink'"
            @click="mode = 'volunteer'"
          >Vorhandener Helfer</button>
        </div>

        <!-- Guest name -->
        <div v-if="mode === 'guest'">
          <label class="label">Name des Helfers</label>
          <input v-model="form.guest_name" class="input" required placeholder="Vor- und Nachname" maxlength="100" />
        </div>

        <!-- Volunteer autocomplete -->
        <div v-else>
          <label class="label">Helfer auswählen</label>
          <!-- Ausgewählter Helfer -->
          <div v-if="selectedVolunteer" class="flex items-center gap-2 px-3 py-2 bg-primary-50 border border-primary-200 rounded-lg mb-2">
            <span class="flex-1 text-sm text-ink">
              {{ selectedVolunteer.display_name || selectedVolunteer.name }}
              <span v-if="selectedVolunteer.email" class="text-muted text-xs ml-1">({{ selectedVolunteer.email }})</span>
            </span>
            <button type="button" class="text-muted hover:text-ink text-xs" @click="clearVolunteer">×</button>
          </div>
          <!-- Sucheingabe -->
          <div v-else class="relative">
            <input
              v-model="volunteerSearch"
              class="input"
              placeholder="Mind. 3 Zeichen eingeben…"
              autocomplete="off"
              @focus="showDropdown = true"
              @blur="onSearchBlur"
            />
            <!-- Dropdown -->
            <div
              v-if="showDropdown && volunteerSearch.length >= 3"
              class="absolute z-20 left-0 right-0 mt-1 bg-soft border border-sand rounded-lg shadow-lg max-h-48 overflow-y-auto"
            >
              <div v-if="!filteredVolunteers.length" class="px-3 py-2 text-xs text-muted">Keine Treffer</div>
              <button
                v-for="v in filteredVolunteers"
                :key="v.id"
                type="button"
                class="w-full text-left px-3 py-2 text-sm hover:bg-bg-warm transition-colors"
                @mousedown.prevent="selectVolunteer(v)"
              >
                <span class="font-medium text-ink">{{ v.display_name || v.name }}</span>
                <span v-if="v.email" class="text-xs text-muted ml-1">{{ v.email }}</span>
              </button>
            </div>
          </div>
          <!-- hidden required field -->
          <input type="text" :value="form.volunteer_id" required class="sr-only" tabindex="-1" aria-hidden="true" />
        </div>

        <div>
          <label class="label">Dienst</label>
          <select v-model="form.shift_id" class="input" required>
            <option value="">Bitte wählen</option>
            <template v-for="section in enrichedGrid" :key="section.date_id">
              <optgroup :label="section.date_formatted">
                <template v-for="{ stand, shiftItems } in section.standShifts" :key="stand.id">
                  <option
                    v-for="item in shiftItems"
                    :key="item.cell.shift_id"
                    :value="item.cell.shift_id"
                    :disabled="item.cell.spots_left === 0"
                  >{{ stand.name }} – {{ item.timeLabel }}</option>
                </template>
              </optgroup>
            </template>
          </select>
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
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { PencilSquareIcon, CalendarIcon } from '@heroicons/vue/24/outline'

const MIN_COL_PX = 160
const PX_PER_MIN = 2.5   // Höhe der Zeitachse: 2.5px pro Minute

const route = useRoute()
const ui = useUiStore()
const grid = ref([])
const loading = ref(true)
const showModal = ref(false)
const form = ref({ guest_name: '', shift_id: '', volunteer_id: '' })
const saveError = ref('')
const mode = ref('guest')
const volunteers = ref([])
const volunteerSearch = ref('')

const selectedVolunteer = ref(null)
const showDropdown = ref(false)

const filteredVolunteers = computed(() => {
  const q = volunteerSearch.value.toLowerCase()
  if (q.length < 3) return []
  return volunteers.value.filter(v => {
    const name = (v.display_name || v.name || '').toLowerCase()
    const email = (v.email || '').toLowerCase()
    return name.includes(q) || email.includes(q)
  })
})

function selectVolunteer(v) {
  selectedVolunteer.value = v
  form.value.volunteer_id = v.id
  volunteerSearch.value = ''
  showDropdown.value = false
}

function clearVolunteer() {
  selectedVolunteer.value = null
  form.value.volunteer_id = ''
  volunteerSearch.value = ''
}

function onSearchBlur() {
  setTimeout(() => { showDropdown.value = false }, 150)
}

// Extrahiert zwei Zeitangaben "HH:MM" aus einem time_range-String
function parseTimeRange(range) {
  const matches = (range || '').match(/(\d{2}:\d{2})/g)
  return { start: matches?.[0] || '00:00', end: matches?.[1] || '00:00' }
}

function toMin(t) {
  const [h, m] = (t || '00:00').split(':').map(Number)
  return h * 60 + m
}

// Wandelt die Grid-Rohdaten in eine für den Stundenplan geeignete Struktur um
const enrichedGrid = computed(() => {
  return grid.value.map(section => {
    // 1. Alle Zeitgrenzen sammeln
    const timeSet = new Set()
    for (const row of section.rows) {
      const { start, end } = parseTimeRange(row.time_range)
      timeSet.add(start)
      timeSet.add(end)
    }
    const allTimes = [...timeSet].sort()
    if (allTimes.length < 2) {
      return { ...section, standShifts: [], hours: [], gridHeight: 120 }
    }

    const startMin = toMin(allTimes[0])
    const endMin = toMin(allTimes[allTimes.length - 1])
    const totalMins = endMin - startMin
    const gridHeight = Math.max(120, totalMins * PX_PER_MIN)

    // 2. Stunden-Markierungen für die Zeitachse
    const startHour = Math.floor(startMin / 60)
    const endHour = Math.ceil(endMin / 60)
    const hours = []
    for (let h = startHour; h <= endHour; h++) {
      const pct = ((h * 60) - startMin) / totalMins * 100
      if (pct >= 0 && pct <= 100) {
        hours.push({ label: `${h}:00`, pct })
      }
    }
    hours.forEach((h, i) => {
      h.ty = i === 0 ? 0 : i === hours.length - 1 ? -100 : -50
    })

    // 3. Pro Stand die Dienst-Blöcke mit prozentigen Position/Höhe
    const standShifts = section.stands.map((stand, si) => {
      const shiftItems = []
      for (const row of section.rows) {
        const cell = row.cells[si]
        if (cell) {
          const { start, end } = parseTimeRange(row.time_range)
          const startPct = (toMin(start) - startMin) / totalMins * 100
          const heightPct = (toMin(end) - toMin(start)) / totalMins * 100
          shiftItems.push({
            cell,
            timeLabel: `${start}–${end}`,
            startPct,
            heightPct,
          })
        }
      }
      return { stand, shiftItems }
    })

    return { ...section, standShifts, hours, gridHeight }
  })
})

onMounted(async () => {
  await Promise.all([load(), loadVolunteers()])
})

async function load() {
  loading.value = true
  try {
    const res = await adminApi.getRegistrationGrid(route.params.slug)
    grid.value = res.data.data
  } finally {
    loading.value = false
  }
}

async function loadVolunteers() {
  try {
    const res = await adminApi.getVolunteers(route.params.slug, { per_page: 500 })
    volunteers.value = res.data.data
  } catch { /* ignore */ }
}

function occupied(cell) {
  return cell.max_volunteers - cell.spots_left
}

function fillPct(cell) {
  if (!cell.max_volunteers) return 0
  return Math.round((occupied(cell) / cell.max_volunteers) * 100)
}

function shiftBlockClass(cell) {
  if (cell.spots_left === 0) return 'bg-green-50 border-green-200'
  const pct = fillPct(cell)
  if (pct >= 75) return 'bg-orange-50 border-orange-200'
  if (pct >= 50) return 'bg-yellow-50 border-yellow-200'
  return 'bg-red-50 border-red-200'
}

function spotBadgeClass(cell) {
  if (cell.spots_left === 0) return 'bg-green-100 text-green-700'
  const pct = fillPct(cell)
  if (pct >= 75) return 'bg-orange-100 text-orange-700'
  if (pct >= 50) return 'bg-yellow-100 text-yellow-700'
  return 'bg-red-100 text-red-700'
}

function fillBarClass(cell) {
  if (cell.spots_left === 0) return 'bg-green-400'
  const pct = fillPct(cell)
  if (pct >= 75) return 'bg-orange-400'
  if (pct >= 50) return 'bg-yellow-400'
  return 'bg-red-400'
}

function openCreate(shiftId) {
  form.value = { guest_name: '', shift_id: shiftId || '', volunteer_id: '' }
  mode.value = 'guest'
  volunteerSearch.value = ''
  selectedVolunteer.value = null
  showDropdown.value = false
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  const payload = { shift_id: form.value.shift_id }
  if (mode.value === 'volunteer') {
    payload.volunteer_id = form.value.volunteer_id
  } else {
    payload.guest_name = form.value.guest_name
  }
  try {
    await adminApi.createRegistration(route.params.slug, payload)
    ui.success('Anmeldung eingetragen')
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteReg(reg, shiftId) {
  const ok = await ui.confirm({
    title: 'Anmeldung entfernen',
    message: `${reg.name} aus dem Dienst entfernen?`,
    confirmText: 'Entfernen',
    danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteRegistration(route.params.slug, reg.id)
    ui.success('Entfernt')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
