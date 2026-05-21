<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Anmeldungen</h1>
      <button class="btn-primary" @click="openCreate(null)">Anmeldung hinzufügen</button>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner size="lg" />
    </div>

    <div v-else-if="!enrichedGrid.length" class="card p-6 text-center text-gray-400">
      Keine Schichten vorhanden.
    </div>

    <!-- Stundenplan: ein Block pro Datum – ein gemeinsamer Scroll-Container -->
    <div v-else class="overflow-x-auto">
    <div class="min-w-max space-y-8">
      <div v-for="section in enrichedGrid" :key="section.date_id">
        <!-- [overflow:clip] clippt Inhalte auf die Rundungen, ohne Scroll-Container zu erzeugen -->
        <div class="card [overflow:clip] !p-0">
          <div class="h-1 bg-primary-500 rounded-t-2xl" />
          <div class="px-5 py-4 border-b border-gray-100 flex items-center gap-2.5">
            <CalendarIcon class="w-5 h-5 text-primary-500 flex-shrink-0" />
            <h2 class="font-semibold text-gray-900">{{ section.date_formatted }}</h2>
          </div>
          <!-- Stand-Spaltenheader -->
          <div class="flex border-b border-gray-100 bg-gray-50">
            <div class="w-14 flex-shrink-0 border-r border-gray-100" />
            <div class="flex flex-1" :style="`min-width: ${section.stands.length * MIN_COL_PX}px`">
              <div
                v-for="stand in section.stands"
                :key="stand.id"
                class="flex-1 px-3 py-3 text-sm font-semibold text-gray-700 border-r border-gray-100 last:border-r-0 min-w-0 truncate"
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
              class="w-14 flex-shrink-0 relative border-r border-gray-100 bg-gray-50/50"
              :style="`height: ${section.gridHeight}px`"
            >
              <div
                v-for="h in section.hours"
                :key="h.label"
                class="absolute right-2 text-[10px] text-gray-400 -translate-y-1/2 whitespace-nowrap"
                :style="`top: ${h.pct}%`"
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
                class="relative flex-1 border-r border-gray-100 last:border-r-0"
                :style="`min-width: ${MIN_COL_PX}px`"
              >
                <!-- Stunden-Rasterlinien -->
                <div
                  v-for="h in section.hours"
                  :key="h.label"
                  class="absolute inset-x-0 border-t border-gray-100/70"
                  :style="`top: ${h.pct}%`"
                />

                <!-- Schicht-Block -->
                <div
                  v-for="item in shiftItems"
                  :key="item.cell.shift_id"
                  class="absolute inset-x-1.5 rounded-xl border flex flex-col overflow-hidden"
                  :class="item.cell.spots_left === 0
                    ? 'bg-green-50 border-green-200'
                    : 'bg-primary-50 border-primary-200'"
                  :style="`top: calc(${item.startPct}% + 2px); height: calc(${item.heightPct}% - 4px); min-height: 2.5rem`"
                >
                  <!-- Kopfzeile: Zeit + Badge -->
                  <div class="flex items-start justify-between gap-1 px-2 pt-2 flex-shrink-0">
                    <span class="text-[10px] font-semibold text-gray-700 leading-tight">{{ item.timeLabel }}</span>
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
                        ? 'bg-white/80 text-gray-600 border border-gray-200'
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
        <div>
          <label class="label">Name des Helfers</label>
          <input v-model="form.guest_name" class="input" required placeholder="Vor- und Nachname" maxlength="100" />
        </div>
        <div>
          <label class="label">Schicht</label>
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
const form = ref({ guest_name: '', shift_id: '' })
const saveError = ref('')

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

    // 3. Pro Stand die Schicht-Blöcke mit prozentigen Position/Höhe
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

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await adminApi.getRegistrationGrid(route.params.slug)
    grid.value = res.data.data
  } finally {
    loading.value = false
  }
}

function occupied(cell) {
  return cell.max_volunteers - cell.spots_left
}

function fillPct(cell) {
  if (!cell.max_volunteers) return 0
  return Math.round((occupied(cell) / cell.max_volunteers) * 100)
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
  form.value = { guest_name: '', shift_id: shiftId || '' }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    await adminApi.createRegistration(route.params.slug, {
      shift_id: form.value.shift_id,
      guest_name: form.value.guest_name,
    })
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
    message: `${reg.name} aus der Schicht entfernen?`,
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
