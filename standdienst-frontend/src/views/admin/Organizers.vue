<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-ink">Organisatoren</h1>
      <button class="btn-primary" @click="openCreate">Neuer Organisator</button>
    </div>

    <div class="card overflow-hidden p-0">
      <!-- Mobile: gestapelte Liste -->
      <div class="md:hidden divide-y divide-sand">
        <div v-for="o in sorted" :key="o.id" class="flex items-start gap-3 px-4 py-3">
          <div class="flex-1 min-w-0">
            <p class="font-medium text-ink text-sm">{{ o.name }}</p>
            <p class="text-xs text-muted mt-0.5 truncate">{{ o.email }}</p>
            <div class="flex items-center gap-2 mt-1.5 flex-wrap">
              <span
                v-if="o.instance_admin_ids?.length"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-700"
              >Instanz-Admin</span>
              <span v-else class="text-xs text-muted">Organisator</span>
              <span class="text-sand">·</span>
              <span class="text-xs text-muted">{{ o.instance_ids?.length ?? 0 }} Instanzen</span>
            </div>
          </div>
          <div class="flex flex-col items-end gap-1.5 flex-shrink-0">
            <button class="text-xs text-primary-600 hover:underline" @click="openEdit(o)">Bearbeiten</button>
            <button class="text-xs text-red-600 hover:underline" @click="deleteOrg(o)">Löschen</button>
          </div>
        </div>
        <div v-if="!sorted.length" class="px-4 py-8 text-center text-muted text-sm">Keine Organisatoren</div>
      </div>

      <!-- Desktop: Tabelle -->
      <table class="hidden md:table w-full text-sm">
        <thead class="bg-bg-brand border-b border-sand">
          <tr>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="name" @sort="toggleSort">Name</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="email" @sort="toggleSort">E-Mail</SortTh>
            <th class="px-4 py-3 text-left font-medium text-muted">Rolle</th>
            <th class="px-4 py-3 text-left font-medium text-muted">Instanzen</th>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in sorted" :key="o.id" class="border-b border-sand hover:bg-bg-warm">
            <td class="px-4 py-3 font-medium text-ink">{{ o.name }}</td>
            <td class="px-4 py-3 text-muted">{{ o.email }}</td>
            <td class="px-4 py-3">
              <span
                v-if="o.instance_admin_ids?.length"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-700"
              >
                Instanz-Admin
              </span>
              <span v-else class="text-xs text-muted">Organisator</span>
            </td>
            <td class="px-4 py-3 text-muted">{{ o.instance_ids?.length ?? 0 }}</td>
            <td class="px-4 py-3 text-right space-x-2">
              <button class="text-xs text-primary-600 hover:underline" @click="openEdit(o)">Bearbeiten</button>
              <button class="text-xs text-red-600 hover:underline" @click="deleteOrg(o)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" :title="editing ? 'Organisator bearbeiten' : 'Neuer Organisator'">
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
        <div><label class="label">E-Mail</label><input v-model="form.email" type="email" class="input" required /></div>
        <div v-if="!editing">
          <label class="label">Passwort <span class="text-xs font-normal text-muted">(optional)</span></label>
          <input v-model="form.password" type="password" class="input" autocomplete="new-password" />
          <p class="text-xs text-muted mt-1">
            Leer lassen → Einladungsmail mit Passwort-Einrichtungslink (7 Tage gültig)
          </p>
        </div>
        <div>
          <label class="label">Zugeordnete Instanzen</label>
          <p class="text-xs text-muted mb-2">Instanz-Admin-Recht erlaubt Zugriff auf Einstellungen und Protokoll der jeweiligen Instanz.</p>
          <div v-if="!instances.length" class="text-xs text-muted py-2">Keine Instanzen vorhanden</div>
          <div v-else class="border border-sand rounded-lg divide-y divide-sand max-h-56 overflow-y-auto">
            <div
              v-for="inst in instances"
              :key="inst.id"
              class="flex items-center gap-3 px-3 py-2 hover:bg-bg-warm"
            >
              <input
                type="checkbox"
                :value="inst.id"
                v-model="form.instance_ids"
                :id="`inst-${inst.id}`"
                class="rounded"
                @change="onInstanceToggle(inst.id)"
              />
              <label :for="`inst-${inst.id}`" class="flex-1 text-sm text-ink/80 cursor-pointer">
                {{ inst.name }}
                <span class="text-xs text-muted font-mono ml-1">{{ inst.slug }}</span>
              </label>
              <label
                v-if="form.instance_ids.includes(inst.id)"
                class="flex items-center gap-1.5 text-xs text-muted cursor-pointer select-none"
              >
                <input
                  type="checkbox"
                  :value="inst.id"
                  v-model="form.instance_admin_ids"
                  class="rounded"
                />
                Instanz-Admin
              </label>
            </div>
          </div>
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
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import { useSort } from '@/composables/useSort'
import Modal from '@/components/Modal.vue'
import SortTh from '@/components/SortTh.vue'

const ui = useUiStore()
const organizers = ref([])
const instances = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ first_name: '', last_name: '', email: '', password: '', instance_ids: [], instance_admin_ids: [] })
const saveError = ref('')

const { sortKey, sortDir, sorted, toggleSort } = useSort(organizers, 'name')

onMounted(async () => {
  await Promise.all([load(), loadInstances()])
})

async function load() {
  const res = await adminApi.getOrganizers({ per_page: 100 })
  organizers.value = res.data.data
}

async function loadInstances() {
  const res = await adminApi.getInstances({ per_page: 200 })
  instances.value = res.data.data
}

function openCreate() {
  editing.value = null
  form.value = { first_name: '', last_name: '', email: '', password: '', instance_ids: [], instance_admin_ids: [] }
  saveError.value = ''
  showModal.value = true
}

function openEdit(o) {
  editing.value = o
  const parts = (o.name || '').split(' ')
  form.value = {
    first_name: o.first_name || parts[0] || '',
    last_name: o.last_name || parts.slice(1).join(' ') || '',
    email: o.email,
    instance_ids: [...(o.instance_ids ?? [])],
    instance_admin_ids: [...(o.instance_admin_ids ?? [])],
  }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateOrganizer(editing.value.id, {
        first_name: form.value.first_name,
        last_name: form.value.last_name,
        email: form.value.email,
        instance_ids: form.value.instance_ids,
        instance_admin_ids: form.value.instance_admin_ids,
      })
      ui.success('Organisator aktualisiert')
    } else {
      await adminApi.createOrganizer(form.value)
      ui.success('Organisator erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

function onInstanceToggle(instanceId) {
  if (!form.value.instance_ids.includes(instanceId)) {
    form.value.instance_admin_ids = form.value.instance_admin_ids.filter(id => id !== instanceId)
  }
}

async function deleteOrg(o) {
  const ok = await ui.confirm({
    title: 'Löschen', message: `${o.name} löschen?`, confirmText: 'Löschen', danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteOrganizer(o.id)
    ui.success('Gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
