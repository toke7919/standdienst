<template>
  <div>
    <div class="flex items-center gap-3 mb-6">
      <RouterLink
        :to="`/admin/${route.params.slug}/volunteers`"
        class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
      >
        <ChevronLeftIcon class="w-4 h-4" />
        Helfer
      </RouterLink>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner size="lg" />
    </div>

    <template v-else-if="volunteer">
      <!-- Info-Karte -->
      <div class="card mb-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h1 class="text-xl font-bold text-gray-900">{{ volunteer.display_name || volunteer.name }}</h1>
            <p class="text-sm text-gray-500 mt-0.5">{{ volunteer.email || 'Keine E-Mail' }}</p>
            <p class="text-xs text-gray-400 mt-1">
              Registriert: {{ formatDate(volunteer.created_at) }}
            </p>
          </div>
          <button class="btn-secondary text-sm flex-shrink-0" @click="openEdit">Bearbeiten</button>
        </div>
        <div class="flex gap-4 mt-4 pt-4 border-t border-gray-100">
          <div class="text-center">
            <p class="text-2xl font-bold text-gray-900">{{ volunteer.registrations?.length ?? 0 }}</p>
            <p class="text-xs text-gray-500">Schichten</p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-gray-900">{{ volunteer.food_donations?.length ?? 0 }}</p>
            <p class="text-xs text-gray-500">Spenden</p>
          </div>
        </div>
      </div>

      <!-- Schicht-Anmeldungen -->
      <div class="card mb-6">
        <h2 class="text-base font-semibold text-gray-800 mb-3">Schicht-Anmeldungen</h2>
        <div v-if="!volunteer.registrations?.length" class="text-sm text-gray-400 py-4 text-center">
          Keine Anmeldungen
        </div>
        <div v-else class="overflow-hidden rounded-lg border border-gray-100">
          <!-- Mobile -->
          <div class="md:hidden divide-y divide-gray-50">
            <div v-for="r in volunteer.registrations" :key="r.id" class="px-4 py-3">
              <p class="font-medium text-sm text-gray-900">{{ r.stand }}</p>
              <p class="text-xs text-gray-500 mt-0.5">{{ r.date }} · {{ r.time_range }}</p>
              <span v-if="r.registered_by_admin" class="inline-block mt-1 text-xs text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">Admin</span>
            </div>
          </div>
          <!-- Desktop -->
          <table class="hidden md:table w-full text-sm">
            <thead class="bg-gray-50 border-b border-gray-100">
              <tr>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Datum</th>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Ort</th>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Zeit</th>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Angemeldet am</th>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Von</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in volunteer.registrations" :key="r.id" class="border-b border-gray-50 hover:bg-gray-50">
                <td class="px-4 py-3 text-gray-700 whitespace-nowrap">{{ r.date }}</td>
                <td class="px-4 py-3 font-medium text-gray-900">{{ r.stand }}</td>
                <td class="px-4 py-3 text-gray-600 whitespace-nowrap">{{ r.time_range }}</td>
                <td class="px-4 py-3 text-gray-500 whitespace-nowrap">{{ formatDate(r.registered_at) }}</td>
                <td class="px-4 py-3">
                  <span v-if="r.registered_by_admin" class="text-xs text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">Admin</span>
                  <span v-else class="text-xs text-gray-400">Helfer</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Essensspenden -->
      <div class="card">
        <h2 class="text-base font-semibold text-gray-800 mb-3">Essensspenden</h2>
        <div v-if="!volunteer.food_donations?.length" class="text-sm text-gray-400 py-4 text-center">
          Keine Spenden
        </div>
        <div v-else class="overflow-hidden rounded-lg border border-gray-100">
          <!-- Mobile -->
          <div class="md:hidden divide-y divide-gray-50">
            <div v-for="f in volunteer.food_donations" :key="f.id" class="px-4 py-3">
              <p class="font-medium text-sm text-gray-900">{{ f.food_type }}</p>
              <p class="text-xs text-gray-500 mt-0.5">{{ f.date }}</p>
              <p v-if="f.description" class="text-xs text-gray-600 mt-0.5">{{ f.description }}</p>
              <span v-if="f.needs_refrigeration" class="inline-block mt-1 text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">Kühlung</span>
            </div>
          </div>
          <!-- Desktop -->
          <table class="hidden md:table w-full text-sm">
            <thead class="bg-gray-50 border-b border-gray-100">
              <tr>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Datum</th>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Kategorie</th>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Beschreibung</th>
                <th class="px-4 py-3 text-left font-medium text-gray-500">Kühlung</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in volunteer.food_donations" :key="f.id" class="border-b border-gray-50 hover:bg-gray-50">
                <td class="px-4 py-3 text-gray-700 whitespace-nowrap">{{ f.date }}</td>
                <td class="px-4 py-3 font-medium text-gray-900">{{ f.food_type }}</td>
                <td class="px-4 py-3 text-gray-600">{{ f.description || '—' }}</td>
                <td class="px-4 py-3">
                  <span v-if="f.needs_refrigeration" class="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">Ja</span>
                  <span v-else class="text-xs text-gray-400">Nein</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <Modal v-if="volunteer" v-model="showModal" title="Helfer bearbeiten">
      <form @submit.prevent="save" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Vorname</label>
            <input v-model="form.first_name" class="input" required />
          </div>
          <div>
            <label class="label">Nachname</label>
            <input v-model="form.last_name" class="input" />
          </div>
        </div>
        <div>
          <label class="label">E-Mail</label>
          <input v-model="form.email" type="email" class="input" />
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
import { useRoute, RouterLink } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import Modal from '@/components/Modal.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { ChevronLeftIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const ui = useUiStore()

const volunteer = ref(null)
const loading = ref(true)
const showModal = ref(false)
const form = ref({ first_name: '', last_name: '', email: '' })
const saveError = ref('')

onMounted(load)

async function load() {
  loading.value = true
  try {
    const res = await adminApi.getVolunteerDetail(route.params.slug, route.params.id)
    volunteer.value = res.data.data
  } finally {
    loading.value = false
  }
}

function formatDate(iso) {
  return iso ? new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }) : '—'
}

function openEdit() {
  form.value = {
    first_name: volunteer.value.first_name || '',
    last_name: volunteer.value.last_name || '',
    email: volunteer.value.email || '',
  }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    await adminApi.updateVolunteer(route.params.slug, volunteer.value.id, form.value)
    ui.success('Helfer aktualisiert')
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}
</script>
