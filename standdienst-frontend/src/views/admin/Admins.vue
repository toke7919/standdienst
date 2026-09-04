<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-ink">Administratoren</h1>
      <button class="btn-primary" @click="openCreate">Neuer Admin</button>
    </div>

    <!-- Mobile: Karten -->
    <div class="md:hidden space-y-2">
      <div
        v-for="a in sorted"
        :key="a.id"
        class="card flex items-start justify-between gap-3 py-3"
      >
        <div class="flex-1 min-w-0">
          <p class="font-medium text-ink truncate">{{ a.name || '—' }}</p>
          <p class="text-xs text-muted mt-0.5 truncate">{{ a.email }}</p>
          <div class="flex items-center gap-1.5 mt-1.5 flex-wrap">
            <span :class="a.is_primary ? 'badge-blue' : 'badge-yellow'">
              {{ a.is_primary ? 'Primär' : 'Standard' }}
            </span>
            <span :class="a.totp_enabled ? 'badge-green' : 'badge-red'">
              2FA {{ a.totp_enabled ? 'aktiv' : 'inaktiv' }}
            </span>
          </div>
        </div>
        <div class="flex flex-col items-end gap-2 shrink-0">
          <button class="text-xs text-primary-600 hover:underline" @click="openEdit(a)">Bearbeiten</button>
          <button v-if="!a.is_primary" class="text-xs text-red-600 hover:underline" @click="deleteAdmin(a)">Löschen</button>
          <span v-else class="text-xs text-sand" title="Primärer Admin ist löschgeschützt">Löschen</span>
        </div>
      </div>
      <p v-if="!admins.length" class="text-center text-muted text-sm py-8">Keine Admins gefunden</p>
    </div>

    <!-- Desktop: Tabelle -->
    <div class="hidden md:block card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-bg-brand border-b border-sand">
          <tr>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="name" @sort="toggleSort">Name</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="email" @sort="toggleSort">E-Mail</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="is_primary" @sort="toggleSort">Typ</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="totp_enabled" @sort="toggleSort">2FA</SortTh>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in sorted" :key="a.id" class="border-b border-sand hover:bg-bg-warm">
            <td class="px-4 py-3 text-ink/80">{{ a.name || '—' }}</td>
            <td class="px-4 py-3 font-medium text-ink">{{ a.email }}</td>
            <td class="px-4 py-3">
              <span :class="a.is_primary ? 'badge-blue' : 'badge-yellow'">
                {{ a.is_primary ? 'Primär' : 'Standard' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span :class="a.totp_enabled ? 'badge-green' : 'badge-red'">
                {{ a.totp_enabled ? 'Aktiv' : 'Inaktiv' }}
              </span>
            </td>
            <td class="px-4 py-3 text-right space-x-2">
              <button class="text-xs text-primary-600 hover:underline" @click="openEdit(a)">Bearbeiten</button>
              <button
                v-if="!a.is_primary"
                class="text-xs text-red-600 hover:underline"
                @click="deleteAdmin(a)"
              >Löschen</button>
              <span v-else class="text-xs text-sand" title="Primärer Admin ist löschgeschützt">Löschen</span>
            </td>
          </tr>
          <tr v-if="!admins.length">
            <td colspan="5" class="px-4 py-8 text-center text-muted">Keine Admins gefunden</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" :title="editing ? 'Admin bearbeiten' : 'Neuer Administrator'">
      <form @submit.prevent="save" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Vorname</label>
            <input v-model="form.first_name" class="input" :required="!editing" />
          </div>
          <div>
            <label class="label">Nachname</label>
            <input v-model="form.last_name" class="input" />
          </div>
        </div>
        <div><label class="label">E-Mail</label><input v-model="form.email" type="email" class="input" required /></div>
        <div>
          <label class="label">{{ editing ? 'Neues Passwort (leer = unverändert)' : 'Passwort' }}</label>
          <input v-model="form.password" type="password" class="input" :required="!editing" />
        </div>
        <div class="flex items-center gap-2">
          <input v-model="form.is_primary" type="checkbox" id="primary" />
          <label for="primary" class="text-sm text-ink/80">Primärer Admin (Löschschutz)</label>
        </div>
        <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
        <div class="flex gap-3 justify-end pt-2">
          <button type="button" class="btn-secondary" @click="showModal = false">Abbrechen</button>
          <button type="submit" class="btn-primary">{{ editing ? 'Speichern' : 'Erstellen' }}</button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import { useSort } from '@/composables/useSort'
import Modal from '@/components/Modal.vue'
import SortTh from '@/components/SortTh.vue'

const ui = useUiStore()
const admins = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ first_name: '', last_name: '', email: '', password: '', is_primary: false })
const saveError = ref('')

const { sortKey, sortDir, sorted, toggleSort } = useSort(admins, 'email')

onMounted(load)

async function load() {
  const res = await adminApi.getAdmins()
  admins.value = res.data.data
}

function openCreate() {
  editing.value = null
  form.value = { first_name: '', last_name: '', email: '', password: '', is_primary: false }
  saveError.value = ''
  showModal.value = true
}

function openEdit(a) {
  editing.value = a
  const parts = (a.name || '').split(' ')
  form.value = {
    first_name: a.first_name || parts[0] || '',
    last_name: a.last_name || parts.slice(1).join(' ') || '',
    email: a.email,
    password: '',
    is_primary: a.is_primary,
  }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    const payload = { ...form.value }
    if (editing.value) {
      if (!payload.password) delete payload.password
      await adminApi.updateAdmin(editing.value.id, payload)
      ui.success('Admin aktualisiert')
    } else {
      await adminApi.createAdmin(payload)
      ui.success('Admin erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteAdmin(a) {
  const ok = await ui.confirm({
    title: 'Admin löschen', message: `${a.email} löschen?`, confirmText: 'Löschen', danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteAdmin(a.id)
    ui.success('Gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
