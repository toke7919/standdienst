<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-ink">Helfer</h1>
      <button class="btn-primary" @click="openCreate">Neuer Helfer</button>
    </div>

    <div class="card mb-4 p-4">
      <input v-model="search" class="input max-w-sm" placeholder="Suchen…" />
    </div>

    <div class="card overflow-hidden p-0">
      <!-- Mobile: gestapelte Liste -->
      <div class="md:hidden divide-y divide-sand">
        <div v-for="v in sortedVolunteers" :key="v.id" class="flex items-start gap-3 px-4 py-3">
          <div class="flex-1 min-w-0">
            <RouterLink
              :to="`/admin/${route.params.slug}/volunteers/${v.id}`"
              class="font-medium text-primary-600 hover:underline text-sm"
            >{{ v.display_name || v.name }}</RouterLink>
            <p class="text-xs text-muted mt-0.5 truncate">{{ v.email || '—' }}</p>
            <div class="flex items-center gap-2 mt-1.5">
              <span class="text-xs text-muted">{{ v.shift_count ?? 0 }} Dienste</span>
              <span class="text-sand">·</span>
              <span class="text-xs text-muted">{{ v.food_count ?? 0 }} Spenden</span>
            </div>
          </div>
          <div class="flex flex-col items-end gap-1.5 flex-shrink-0">
            <button class="text-xs text-primary-600 hover:underline" @click="openEdit(v)">Bearbeiten</button>
            <button class="text-xs text-red-600 hover:underline" @click="deleteVol(v)">Löschen</button>
          </div>
        </div>
        <div v-if="!sortedVolunteers.length" class="px-4 py-8 text-center text-muted text-sm">Keine Helfer</div>
      </div>

      <!-- Desktop: Tabelle -->
      <table class="hidden md:table w-full text-sm">
        <thead class="bg-bg-brand border-b border-sand">
          <tr>
            <SortTh :sort-key="localSortKey" :sort-dir="localSortDir" field="name" @sort="toggleLocalSort">Name</SortTh>
            <SortTh :sort-key="localSortKey" :sort-dir="localSortDir" field="email" @sort="toggleLocalSort">E-Mail</SortTh>
            <SortTh :sort-key="localSortKey" :sort-dir="localSortDir" field="created_at" @sort="toggleLocalSort">Angemeldet</SortTh>
            <SortTh :sort-key="localSortKey" :sort-dir="localSortDir" field="shift_count" @sort="toggleLocalSort" class="text-right">Dienste</SortTh>
            <SortTh :sort-key="localSortKey" :sort-dir="localSortDir" field="food_count" @sort="toggleLocalSort" class="text-right">Spenden</SortTh>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in sortedVolunteers" :key="v.id" class="border-b border-sand hover:bg-bg-warm">
            <td class="px-4 py-3 font-medium">
              <RouterLink
                :to="`/admin/${route.params.slug}/volunteers/${v.id}`"
                class="text-primary-600 hover:underline"
              >{{ v.display_name || v.name }}</RouterLink>
            </td>
            <td class="px-4 py-3 text-muted">{{ v.email || '—' }}</td>
            <td class="px-4 py-3 text-muted whitespace-nowrap">{{ formatDate(v.created_at) }}</td>
            <td class="px-4 py-3 text-right text-ink/80 tabular-nums">{{ v.shift_count ?? 0 }}</td>
            <td class="px-4 py-3 text-right text-ink/80 tabular-nums">{{ v.food_count ?? 0 }}</td>
            <td class="px-4 py-3 text-right space-x-2">
              <button class="text-xs text-primary-600 hover:underline" @click="openEdit(v)">Bearbeiten</button>
              <button class="text-xs text-red-600 hover:underline" @click="deleteVol(v)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination v-model:page="page" :pages="pages" :total="total" :per-page="perPage" @update:page="load" />

    <Modal v-model="showModal" :title="editing ? 'Helfer bearbeiten' : 'Neuer Helfer'">
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
        <div v-if="!editing">
          <label class="label">Passwort</label>
          <input v-model="form.password" type="password" class="input" placeholder="Leer lassen = Willkommens-E-Mail" />
          <p v-if="form.email && !form.password" class="text-xs text-muted mt-1">
            Helfer erhält eine Willkommens-E-Mail zum Einrichten des Passworts.
          </p>
        </div>
        <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
        <div class="flex gap-3 justify-end pt-2">
          <button type="button" class="btn-secondary" @click="showModal = false">Abbrechen</button>
          <button type="submit" class="btn-primary">Speichern</button>
        </div>

        <!-- DSGVO-Aktionen (nur für Instanz-Admins / globale Admins) -->
        <template v-if="editing && (auth.isAdmin || auth.isInstanceAdminFor(route.params.slug))">
          <hr class="border-sand" />
          <div class="space-y-2">
            <p class="text-xs font-semibold text-muted uppercase tracking-wide">DSGVO</p>
            <div class="flex flex-wrap gap-2">
              <button
                v-if="editing.email"
                type="button"
                class="btn-secondary text-xs"
                :disabled="auskunftSending"
                @click="sendAuskunft"
              >
                <LoadingSpinner v-if="auskunftSending" size="sm" class="mr-1" />
                Datenauskunft senden (Art. 15)
              </button>
              <span v-else class="text-xs text-muted self-center">Keine E-Mail – Datenauskunft nicht möglich</span>
              <button
                type="button"
                class="btn-danger text-xs"
                @click="pseudonymize"
              >
                Pseudonymisieren (Art. 17)
              </button>
            </div>
          </div>
        </template>
      </form>
    </Modal>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { adminApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useSort } from '@/composables/useSort'
import Modal from '@/components/Modal.vue'
import Pagination from '@/components/Pagination.vue'
import SortTh from '@/components/SortTh.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()

const volunteers = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const perPage = 20
const search = ref('')
const showModal = ref(false)
const editing = ref(null)
const { sortKey: localSortKey, sortDir: localSortDir, sorted: sortedVolunteers, toggleSort: toggleLocalSort } = useSort(volunteers, 'name')
const form = ref({ first_name: '', last_name: '', email: '', password: '' })
const saveError = ref('')

onMounted(load)
watch(search, () => { page.value = 1; load() })

async function load() {
  const res = await adminApi.getVolunteers(route.params.slug, {
    page: page.value, per_page: perPage, search: search.value,
  })
  const d = res.data
  volunteers.value = d.data
  pages.value = d.pages
  total.value = d.total
}

function formatDate(iso) {
  return iso ? new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }) : ''
}

function openCreate() {
  editing.value = null
  form.value = { first_name: '', last_name: '', email: '', password: '' }
  saveError.value = ''
  showModal.value = true
}

function openEdit(v) {
  editing.value = v
  form.value = {
    first_name: v.first_name || v.name || '',
    last_name: v.last_name || '',
    email: v.email || '',
  }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateVolunteer(route.params.slug, editing.value.id, form.value)
      ui.success('Helfer aktualisiert')
    } else {
      await adminApi.createVolunteer(route.params.slug, form.value)
      ui.success('Helfer erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteVol(v) {
  const ok = await ui.confirm({
    title: 'Helfer löschen',
    message: `${v.name} wirklich löschen?`,
    confirmText: 'Löschen',
    danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteVolunteer(route.params.slug, v.id)
    ui.success('Gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}

// ── DSGVO-Aktionen ─────────────────────────────────────────────────────────
const auskunftSending = ref(false)

async function sendAuskunft() {
  auskunftSending.value = true
  try {
    await adminApi.sendDsgvoAuskunft(route.params.slug, editing.value.id)
    ui.success('Datenauskunft wurde versendet')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  } finally {
    auskunftSending.value = false
  }
}

async function pseudonymize() {
  const name = editing.value.display_name || editing.value.name
  const ok = await ui.confirm({
    title: 'Helfer pseudonymisieren',
    message: `${name} wirklich pseudonymisieren? Name und E-Mail werden unwiderruflich gelöscht. Dienstanmeldungen bleiben anonymisiert erhalten.`,
    confirmText: 'Pseudonymisieren',
    danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteVolunteer(route.params.slug, editing.value.id)
    ui.success('Helfer pseudonymisiert')
    showModal.value = false
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
