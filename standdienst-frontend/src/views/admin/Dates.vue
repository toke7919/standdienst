<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-ink">Termine</h1>
      <button class="btn-primary" @click="openCreate">Neuer Termin</button>
    </div>

    <div class="space-y-2">
      <div
        v-for="d in dates"
        :key="d.id"
        class="group bg-soft rounded-md border border-sand shadow-sm px-5 py-4 flex items-center gap-4 hover:border-primary-200 transition-colors duration-150"
      >
        <div class="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center flex-shrink-0">
          <CalendarIcon class="w-5 h-5 text-primary-600" />
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <p class="font-semibold text-ink">{{ d.formatted }}</p>
            <span
              v-if="d.is_draft"
              class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800"
            >Entwurf</span>
          </div>
          <p v-if="d.label" class="text-sm text-muted mt-0.5">{{ d.label }}</p>
        </div>
        <div class="flex items-center gap-3">
          <button class="text-sm text-primary-600 hover:text-primary-800 font-medium" @click="openEdit(d)">Bearbeiten</button>
          <span class="text-sand">|</span>
          <button class="text-sm text-muted hover:text-ink font-medium" @click="openDuplicate(d)">Duplizieren</button>
          <span class="text-sand">|</span>
          <button class="text-sm text-red-500 hover:text-red-700 font-medium" @click="deleteDate(d)">Löschen</button>
        </div>
      </div>

      <div v-if="!dates.length" class="bg-soft rounded-md border border-sand shadow-sm py-16 text-center">
        <CalendarIcon class="w-10 h-10 text-primary-200 mx-auto mb-3" />
        <p class="text-muted text-sm">Noch keine Termine angelegt</p>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <Modal v-model="showModal" :title="editing ? 'Termin bearbeiten' : 'Neuer Termin'">
      <form @submit.prevent="save" class="space-y-4">
        <div>
          <label class="label">Datum</label>
          <input v-model="form.date" type="date" class="input appearance-none" required />
        </div>
        <div>
          <label class="label">Beschriftung (optional)</label>
          <input v-model="form.label" class="input" placeholder="z.B. Aufbautag" />
        </div>
        <div class="flex items-center gap-3">
          <input id="is_draft" v-model="form.is_draft" type="checkbox" class="rounded border-sand text-primary-600 focus:ring-primary-500" />
          <label for="is_draft" class="text-sm text-ink">Entwurf</label>
        </div>
        <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>
        <div class="flex gap-3 justify-end pt-2">
          <button type="button" class="btn-secondary" @click="showModal = false">Abbrechen</button>
          <button type="submit" class="btn-primary">Speichern</button>
        </div>
      </form>
    </Modal>

    <!-- Duplicate Modal -->
    <Modal v-model="showDuplicateModal" title="Termin duplizieren">
      <form @submit.prevent="saveDuplicate" class="space-y-4">
        <p class="text-sm text-muted">
          Kopiert alle Dienste von <strong>{{ duplicateSource?.formatted }}</strong> auf das neue Datum.
          Der neue Termin wird als Entwurf angelegt.
        </p>
        <div>
          <label class="label">Zieldatum</label>
          <input v-model="duplicateDate" type="date" class="input appearance-none" required />
        </div>
        <p v-if="duplicateError" class="text-sm text-red-600">{{ duplicateError }}</p>
        <div class="flex gap-3 justify-end pt-2">
          <button type="button" class="btn-secondary" @click="showDuplicateModal = false">Abbrechen</button>
          <button type="submit" class="btn-primary">Duplizieren</button>
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
import { CalendarIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const ui = useUiStore()
const dates = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ date: '', label: '', is_draft: false })
const saveError = ref('')

const showDuplicateModal = ref(false)
const duplicateSource = ref(null)
const duplicateDate = ref('')
const duplicateError = ref('')

onMounted(load)

async function load() {
  const res = await adminApi.getDates(route.params.slug)
  dates.value = res.data.data
}

function openCreate() {
  editing.value = null
  form.value = { date: '', label: '', is_draft: false }
  saveError.value = ''
  showModal.value = true
}

function openEdit(d) {
  editing.value = d
  form.value = { date: d.date, label: d.label || '', is_draft: d.is_draft ?? false }
  saveError.value = ''
  showModal.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editing.value) {
      await adminApi.updateDate(route.params.slug, editing.value.id, form.value)
      ui.success('Termin aktualisiert')
    } else {
      await adminApi.createDate(route.params.slug, form.value)
      ui.success('Termin erstellt')
    }
    showModal.value = false
    await load()
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  }
}

function openDuplicate(d) {
  duplicateSource.value = d
  duplicateDate.value = ''
  duplicateError.value = ''
  showDuplicateModal.value = true
}

async function saveDuplicate() {
  duplicateError.value = ''
  try {
    await adminApi.duplicateDate(route.params.slug, duplicateSource.value.id, { date: duplicateDate.value })
    ui.success('Termin dupliziert (als Entwurf angelegt)')
    showDuplicateModal.value = false
    await load()
  } catch (e) {
    duplicateError.value = e.response?.data?.error || 'Fehler'
  }
}

async function deleteDate(d) {
  const ok = await ui.confirm({
    title: 'Termin löschen', message: `${d.formatted} löschen?`, confirmText: 'Löschen', danger: true,
  })
  if (!ok) return
  try {
    await adminApi.deleteDate(route.params.slug, d.id)
    ui.success('Gelöscht')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}
</script>
