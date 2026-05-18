<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Administratoren</h1>
      <button class="btn-primary" @click="openCreate">Neuer Admin</button>
    </div>

    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Name</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">E-Mail</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">Primär</th>
            <th class="px-4 py-3 text-left font-medium text-gray-500">2FA</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in admins" :key="a.id" class="border-b border-gray-50 hover:bg-gray-50">
            <td class="px-4 py-3 text-gray-700">{{ a.name || '—' }}</td>
            <td class="px-4 py-3 font-medium text-gray-900">{{ a.email }}</td>
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
              <button class="text-xs text-red-600 hover:underline" @click="deleteAdmin(a)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" title="Neuer Administrator">
      <form @submit.prevent="save" class="space-y-4">
        <div><label class="label">Name</label><input v-model="form.name" class="input" /></div>
        <div><label class="label">E-Mail</label><input v-model="form.email" type="email" class="input" required /></div>
        <div><label class="label">Passwort</label><input v-model="form.password" type="password" class="input" required /></div>
        <div class="flex items-center gap-2">
          <input v-model="form.is_primary" type="checkbox" id="primary" />
          <label for="primary" class="text-sm text-gray-700">Primärer Admin (Kontaktformular-Empfänger)</label>
        </div>
        <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
        <div class="flex gap-3 justify-end pt-2">
          <button type="button" class="btn-secondary" @click="showModal = false">Abbrechen</button>
          <button type="submit" class="btn-primary">Erstellen</button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import Modal from '@/components/Modal.vue'

const ui = useUiStore()
const admins = ref([])
const showModal = ref(false)
const form = ref({ name: '', email: '', password: '', is_primary: false })
const saveError = ref('')

onMounted(load)

async function load() {
  const res = await adminApi.getAdmins()
  admins.value = res.data.data
}

function openCreate() {
  form.value = { name: '', email: '', password: '', is_primary: false }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    await adminApi.createAdmin(form.value)
    ui.success('Admin erstellt')
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
