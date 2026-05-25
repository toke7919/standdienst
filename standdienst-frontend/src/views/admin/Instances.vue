<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-ink">Instanzen</h1>
      <button class="btn-primary" @click="openCreate">Neue Instanz</button>
    </div>

    <div class="card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead class="bg-bg-brand border-b border-sand">
          <tr>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="name" @sort="toggleSort">Name</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="slug" @sort="toggleSort">Slug</SortTh>
            <SortTh :sort-key="sortKey" :sort-dir="sortDir" field="is_active" @sort="toggleSort">Status</SortTh>
            <th class="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="inst in sorted" :key="inst.id" class="border-b border-sand hover:bg-bg-warm">
            <td class="px-4 py-3 font-medium text-ink">{{ inst.name }}</td>
            <td class="px-4 py-3 text-muted">{{ inst.slug }}</td>
            <td class="px-4 py-3">
              <span :class="inst.is_active ? 'badge-green' : 'badge-red'">
                {{ inst.is_active ? 'Aktiv' : 'Inaktiv' }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <button class="text-xs text-primary-600 hover:underline mr-3" @click="openEdit(inst)">
                Bearbeiten
              </button>
              <button class="text-xs text-red-600 hover:underline" @click="deleteInst(inst)">
                Löschen
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" :title="editing ? 'Instanz bearbeiten' : 'Neue Instanz'">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="label">Name</label>
          <input v-model="form.name" class="input" required />
        </div>
        <div>
          <label class="label">Slug (URL-Kürzel)</label>
          <input v-model="form.slug" class="input" required :disabled="!!editing" />
        </div>
        <div class="flex items-center gap-2">
          <input v-model="form.is_active" type="checkbox" id="active" class="rounded" />
          <label for="active" class="text-sm text-ink/80">Aktiv</label>
        </div>

        <div class="border-t border-sand pt-4 space-y-3">
          <h3 class="text-sm font-semibold text-ink/80">Kontaktdaten (Impressum / Datenschutz)</h3>
          <p class="text-xs text-muted">
            Werden als Platzhalter in die globalen Impressum- und Datenschutz-Vorlagen eingesetzt.
          </p>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label text-xs">Organisation / Verein</label>
              <input v-model="form.contact_organisation" class="input text-sm" placeholder="Musterverein e.V." />
            </div>
            <div>
              <label class="label text-xs">Verantwortliche Person</label>
              <input v-model="form.contact_person" class="input text-sm" placeholder="Max Mustermann" />
            </div>
            <div>
              <label class="label text-xs">Straße &amp; Hausnummer</label>
              <input v-model="form.contact_street" class="input text-sm" placeholder="Musterstraße 1" />
            </div>
            <div>
              <label class="label text-xs">PLZ &amp; Ort</label>
              <input v-model="form.contact_zip_city" class="input text-sm" placeholder="12345 Musterstadt" />
            </div>
            <div>
              <label class="label text-xs">E-Mail</label>
              <input v-model="form.contact_email" class="input text-sm" type="email" placeholder="kontakt@beispiel.de" />
            </div>
            <div>
              <label class="label text-xs">Telefon</label>
              <input v-model="form.contact_phone" class="input text-sm" type="tel" placeholder="+49 123 456789" />
            </div>
            <div>
              <label class="label text-xs">Ansprechpartner <span class="text-muted font-normal">(Platzhalter: {{asp}})</span></label>
              <input v-model="form.contact_asp" class="input text-sm" placeholder="Für Rückfragen: Max Muster" />
            </div>
            <div>
              <label class="label text-xs">Ansprechpartner E-Mail <span class="text-muted font-normal">({{asp-email}})</span></label>
              <input v-model="form.contact_asp_email" class="input text-sm" type="email" placeholder="max@beispiel.de" />
            </div>
          </div>
        </div>

        <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
        <div class="flex gap-3 justify-end pt-2">
          <button type="button" class="btn-secondary" @click="showModal = false">Abbrechen</button>
          <button type="submit" class="btn-primary" :disabled="saving">Speichern</button>
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
const instances = ref([])
const { sortKey, sortDir, sorted, toggleSort } = useSort(instances, 'name')
const showModal = ref(false)
const editing = ref(null)
const _emptyForm = () => ({
  name: '', slug: '', is_active: true,
  contact_organisation: '', contact_person: '', contact_street: '',
  contact_zip_city: '', contact_email: '', contact_phone: '',
  contact_asp: '', contact_asp_email: '',
})
const form = ref(_emptyForm())
const saving = ref(false)
const saveError = ref('')

onMounted(load)

async function load() {
  const res = await adminApi.getInstances({ per_page: 100 })
  instances.value = res.data.data
}

function openCreate() {
  editing.value = null
  form.value = _emptyForm()
  saveError.value = ''
  showModal.value = true
}

function openEdit(inst) {
  editing.value = inst
  form.value = {
    name: inst.name, slug: inst.slug, is_active: inst.is_active,
    contact_organisation: inst.contact_organisation || '',
    contact_person: inst.contact_person || '',
    contact_street: inst.contact_street || '',
    contact_zip_city: inst.contact_zip_city || '',
    contact_email: inst.contact_email || '',
    contact_phone: inst.contact_phone || '',
    contact_asp: inst.contact_asp || '',
    contact_asp_email: inst.contact_asp_email || '',
  }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateInstance(editing.value.id, form.value)
      ui.success('Instanz aktualisiert')
    } else {
      await adminApi.createInstance(form.value)
      ui.success('Instanz erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}

async function deleteInst(inst) {
  const ok = await ui.confirm({
    title: 'Instanz löschen',
    message: `"${inst.name}" wirklich löschen? Alle Daten gehen verloren!`,
    confirmText: 'Löschen',
    danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteInstance(inst.id)
    ui.success('Instanz gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler beim Löschen')
  }
}
</script>
