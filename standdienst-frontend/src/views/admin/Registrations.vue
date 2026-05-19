<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Anmeldungen</h1>
      <button class="btn-primary" @click="openCreate(null)">Anmeldung hinzufügen</button>
    </div>

    <div v-if="loading" class="text-center py-12 text-gray-400">Laden…</div>

    <div v-else-if="!grid.length" class="card p-6 text-center text-gray-400">
      Keine Schichten vorhanden.
    </div>

    <div v-else class="space-y-8">
      <div v-for="section in grid" :key="section.date_id">
        <h2 class="text-lg font-semibold text-gray-700 mb-3">{{ section.date_formatted }}</h2>
        <div class="card overflow-x-auto p-0">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 border-b border-gray-100">
              <tr>
                <th class="px-4 py-3 text-left text-gray-500 font-medium w-32 shrink-0">Zeit</th>
                <th
                  v-for="stand in section.stands"
                  :key="stand.id"
                  class="px-4 py-3 text-left text-gray-700 font-semibold min-w-[180px]"
                >
                  {{ stand.name }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in section.rows"
                :key="row.time_range"
                class="border-t border-gray-100"
              >
                <td class="px-4 py-3 text-gray-500 font-medium whitespace-nowrap align-top">
                  {{ row.time_range }}
                </td>
                <td
                  v-for="(cell, i) in row.cells"
                  :key="i"
                  class="px-4 py-3 align-top min-w-[180px]"
                >
                  <template v-if="cell">
                    <!-- Kopfzeile: Belegung links, Balloon rechts -->
                    <div class="flex items-center justify-between mb-1.5 gap-2">
                      <span class="text-xs text-gray-500 whitespace-nowrap">
                        {{ occupied(cell) }}/{{ cell.max_volunteers }} Plätze
                      </span>
                      <span :class="['text-xs font-semibold px-2 py-0.5 rounded-full whitespace-nowrap', spotBadgeClass(cell)]">
                        {{ cell.spots_left === 0 ? 'Voll' : `${cell.spots_left} frei` }}
                      </span>
                    </div>

                    <!-- Fortschrittsbalken -->
                    <div class="w-full h-1.5 bg-gray-100 rounded-full mb-2.5 overflow-hidden">
                      <div
                        :class="['h-full rounded-full transition-all duration-300', fillBarClass(cell)]"
                        :style="{ width: `${fillPct(cell)}%` }"
                      />
                    </div>

                    <!-- Anmeldungen -->
                    <div v-if="cell.registrations.length" class="flex flex-wrap gap-1 mb-2">
                      <span
                        v-for="reg in cell.registrations"
                        :key="reg.id"
                        :class="['inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full',
                          reg.by_admin
                            ? 'bg-gray-100 text-gray-600'
                            : 'bg-primary-100 text-primary-700'
                        ]"
                        :title="reg.by_admin ? 'Eingetragen durch Admin/Organisator' : 'Selbst angemeldet'"
                      >
                        <PencilSquareIcon v-if="reg.by_admin" class="w-3 h-3 shrink-0 opacity-60" />
                        {{ reg.name }}
                        <button
                          type="button"
                          class="opacity-50 hover:opacity-100 leading-none ml-0.5"
                          @click="deleteReg(reg, cell.shift_id)"
                        >×</button>
                      </span>
                    </div>

                    <!-- Eintragen-Button -->
                    <button
                      v-if="cell.spots_left > 0"
                      type="button"
                      class="text-xs text-primary-600 hover:text-primary-800 font-medium"
                      @click="openCreate(cell.shift_id)"
                    >+ Eintragen</button>
                  </template>
                  <template v-else>
                    <span class="text-gray-300 text-xs">–</span>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
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
            <template v-for="section in grid" :key="section.date_id">
              <optgroup :label="section.date_formatted">
                <template v-for="row in section.rows" :key="row.time_range">
                  <template v-for="(cell, i) in row.cells" :key="i">
                    <option
                      v-if="cell && cell.spots_left > 0"
                      :value="cell.shift_id"
                    >{{ section.stands[i]?.name }} – {{ row.time_range }}</option>
                  </template>
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
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import Modal from '@/components/Modal.vue'
import { PencilSquareIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const ui = useUiStore()
const grid = ref([])
const loading = ref(true)
const showModal = ref(false)
const form = ref({ guest_name: '', shift_id: '' })
const saveError = ref('')

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
  if (cell.spots_left === 0) return 'bg-red-100 text-red-700'
  const pct = fillPct(cell)
  if (pct >= 75) return 'bg-orange-100 text-orange-700'
  if (pct >= 50) return 'bg-yellow-100 text-yellow-700'
  return 'bg-green-100 text-green-700'
}

function fillBarClass(cell) {
  if (cell.spots_left === 0) return 'bg-red-400'
  const pct = fillPct(cell)
  if (pct >= 75) return 'bg-orange-400'
  if (pct >= 50) return 'bg-yellow-400'
  return 'bg-green-400'
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
