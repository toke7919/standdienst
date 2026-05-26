<template>
  <div>
    <div class="flex items-center gap-3 mb-6">
      <RouterLink
        :to="`/admin/${route.params.slug}/volunteers`"
        class="text-sm text-muted hover:text-ink/80 flex items-center gap-1"
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
            <h1 class="text-xl font-bold text-ink">{{ volunteer.display_name || volunteer.name }}</h1>
            <p class="text-sm text-muted mt-0.5">{{ volunteer.email || 'Keine E-Mail' }}</p>
            <p class="text-xs text-muted mt-1">
              Registriert: {{ formatDate(volunteer.created_at) }}
            </p>
          </div>
          <button class="btn-secondary text-sm flex-shrink-0" @click="openEdit">Bearbeiten</button>
        </div>
        <div class="flex gap-4 mt-4 pt-4 border-t border-sand">
          <div class="text-center">
            <p class="text-2xl font-bold text-ink">{{ volunteer.registrations?.length ?? 0 }}</p>
            <p class="text-xs text-muted">Dienste</p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-ink">{{ volunteer.food_donations?.length ?? 0 }}</p>
            <p class="text-xs text-muted">Spenden</p>
          </div>
        </div>
      </div>

      <!-- Dienst-Anmeldungen -->
      <div class="card mb-6">
        <h2 class="text-base font-semibold text-ink mb-3">Dienst-Anmeldungen</h2>
        <div v-if="!volunteer.registrations?.length" class="text-sm text-muted py-4 text-center">
          Keine Anmeldungen
        </div>
        <div v-else class="overflow-hidden rounded-lg border border-sand">
          <!-- Mobile -->
          <div class="md:hidden divide-y divide-sand">
            <div v-for="r in volunteer.registrations" :key="r.id" class="px-4 py-3">
              <p class="font-medium text-sm text-ink">{{ r.stand }}</p>
              <p class="text-xs text-muted mt-0.5">{{ r.date }} · {{ r.time_range }}</p>
              <span v-if="r.registered_by_admin" class="inline-block mt-1 text-xs text-primary-600 bg-primary-50 px-1.5 py-0.5 rounded">Admin</span>
            </div>
          </div>
          <!-- Desktop -->
          <table class="hidden md:table w-full text-sm">
            <thead class="bg-bg-brand border-b border-sand">
              <tr>
                <th class="px-4 py-3 text-left font-medium text-muted">Datum</th>
                <th class="px-4 py-3 text-left font-medium text-muted">Ort</th>
                <th class="px-4 py-3 text-left font-medium text-muted">Zeit</th>
                <th class="px-4 py-3 text-left font-medium text-muted">Angemeldet am</th>
                <th class="px-4 py-3 text-left font-medium text-muted">Von</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in volunteer.registrations" :key="r.id" class="border-b border-sand hover:bg-bg-warm">
                <td class="px-4 py-3 text-ink/80 whitespace-nowrap">{{ r.date }}</td>
                <td class="px-4 py-3 font-medium text-ink">{{ r.stand }}</td>
                <td class="px-4 py-3 text-ink/80 whitespace-nowrap">{{ r.time_range }}</td>
                <td class="px-4 py-3 text-muted whitespace-nowrap">{{ formatDate(r.registered_at) }}</td>
                <td class="px-4 py-3">
                  <span v-if="r.registered_by_admin" class="text-xs text-primary-600 bg-primary-50 px-1.5 py-0.5 rounded">Admin</span>
                  <span v-else class="text-xs text-muted">Helfer</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- DSGVO-Aktionen -->
      <div class="card mb-6">
        <h2 class="text-base font-semibold text-ink mb-1">DSGVO</h2>
        <p class="text-xs text-muted mb-4">Aktionen gemäß Datenschutz-Grundverordnung</p>
        <div class="flex flex-wrap gap-3">
          <button
            v-if="volunteer.email"
            class="btn-secondary text-sm"
            :disabled="auskunftLoading"
            @click="sendAuskunft"
          >
            <LoadingSpinner v-if="auskunftLoading" size="sm" />
            Datenauskunft senden (Art. 15)
          </button>
          <span v-else class="text-xs text-muted self-center">Keine E-Mail – Datenauskunft nicht möglich</span>
          <button
            v-if="!volunteer.deleted_at"
            class="btn-secondary text-sm text-red-600 border-red-200 hover:bg-red-50"
            :disabled="deleteLoading"
            @click="softDelete"
          >
            <LoadingSpinner v-if="deleteLoading" size="sm" />
            Pseudonymisieren (Art. 17)
          </button>
          <span v-else class="text-xs text-muted self-center italic">Bereits pseudonymisiert</span>
        </div>
      </div>

      <!-- Essensspenden -->
      <div class="card">
        <h2 class="text-base font-semibold text-ink mb-3">Essensspenden</h2>
        <div v-if="!volunteer.food_donations?.length" class="text-sm text-muted py-4 text-center">
          Keine Spenden
        </div>
        <div v-else class="overflow-hidden rounded-lg border border-sand">
          <!-- Mobile -->
          <div class="md:hidden divide-y divide-sand">
            <div v-for="f in volunteer.food_donations" :key="f.id" class="px-4 py-3">
              <p class="font-medium text-sm text-ink">{{ f.food_type }}</p>
              <p class="text-xs text-muted mt-0.5">{{ f.date }}</p>
              <p v-if="f.description" class="text-xs text-ink/80 mt-0.5">{{ f.description }}</p>
              <span v-if="f.needs_refrigeration" class="inline-block mt-1 text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">Kühlung</span>
            </div>
          </div>
          <!-- Desktop -->
          <table class="hidden md:table w-full text-sm">
            <thead class="bg-bg-brand border-b border-sand">
              <tr>
                <th class="px-4 py-3 text-left font-medium text-muted">Datum</th>
                <th class="px-4 py-3 text-left font-medium text-muted">Kategorie</th>
                <th class="px-4 py-3 text-left font-medium text-muted">Beschreibung</th>
                <th class="px-4 py-3 text-left font-medium text-muted">Kühlung</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in volunteer.food_donations" :key="f.id" class="border-b border-sand hover:bg-bg-warm">
                <td class="px-4 py-3 text-ink/80 whitespace-nowrap">{{ f.date }}</td>
                <td class="px-4 py-3 font-medium text-ink">{{ f.food_type }}</td>
                <td class="px-4 py-3 text-ink/80">{{ f.description || '—' }}</td>
                <td class="px-4 py-3">
                  <span v-if="f.needs_refrigeration" class="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">Ja</span>
                  <span v-else class="text-xs text-muted">Nein</span>
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
const auskunftLoading = ref(false)
const deleteLoading = ref(false)

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

async function sendAuskunft() {
  auskunftLoading.value = true
  try {
    await adminApi.sendDsgvoAuskunft(route.params.slug, volunteer.value.id)
    ui.success('Datenauskunft wurde versendet')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Versand fehlgeschlagen')
  } finally {
    auskunftLoading.value = false
  }
}

async function softDelete() {
  const ok = await ui.confirm({
    title: 'Helfer pseudonymisieren',
    message: `${volunteer.value.display_name || volunteer.value.name} wirklich pseudonymisieren? Name und E-Mail werden unwiderruflich gelöscht. Dienstanmeldungen bleiben anonymisiert erhalten.`,
    danger: true,
  })
  if (!ok) return
  deleteLoading.value = true
  try {
    await adminApi.deleteVolunteer(route.params.slug, volunteer.value.id)
    ui.success('Helfer pseudonymisiert')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  } finally {
    deleteLoading.value = false
  }
}
</script>
