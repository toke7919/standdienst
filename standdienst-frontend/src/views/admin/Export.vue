<template>
  <div>
    <h1 class="text-2xl font-bold text-ink mb-6">Export</h1>

    <div v-if="loadingDates" class="flex justify-center py-12">
      <LoadingSpinner size="lg" />
    </div>

    <div v-else class="grid gap-6 max-w-2xl">

      <!-- Termin-Selektion (gemeinsam für beide Export-Typen) -->
      <div class="card">
        <h2 class="text-base font-semibold text-ink mb-1">Termine auswählen</h2>
        <p class="text-sm text-muted mb-4">Nur die gewählten Termine werden exportiert.</p>

        <div v-if="!dates.length" class="text-sm text-muted">Keine Termine vorhanden.</div>

        <div v-else class="space-y-2">
          <!-- Alle auswählen -->
          <label class="flex items-center gap-3 cursor-pointer group">
            <input
              type="checkbox"
              :checked="allSelected"
              :indeterminate.prop="someSelected && !allSelected"
              class="rounded border-sand text-primary-600 focus:ring-primary-500"
              @change="toggleAll"
            />
            <span class="text-sm font-semibold text-ink">Alle auswählen</span>
          </label>

          <div class="border-t border-sand pt-2 space-y-1.5">
            <label
              v-for="d in dates"
              :key="d.id"
              class="flex items-center gap-3 cursor-pointer group"
            >
              <input
                v-model="selectedIds"
                :value="d.id"
                type="checkbox"
                class="rounded border-sand text-primary-600 focus:ring-primary-500"
              />
              <span class="text-sm text-ink">{{ d.formatted }}</span>
              <span
                v-if="d.is_draft"
                class="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-amber-100 text-amber-800"
              >Entwurf</span>
              <span v-if="d.label" class="text-xs text-muted ml-1">{{ d.label }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Dienste-Export -->
      <div class="card">
        <h2 class="text-base font-semibold text-ink mb-1">Dienste</h2>
        <p class="text-sm text-muted mb-4">Dienstplan der gewählten Termine, je Tag eine Seite.</p>

        <div class="flex flex-wrap gap-3 mb-3">
          <button
            class="btn-secondary"
            :disabled="!selectedIds.length || busyDienste"
            @click="downloadPdf('dienste')"
          >
            <ArrowDownTrayIcon class="w-4 h-4" />
            PDF herunterladen
          </button>
          <button
            class="btn-secondary"
            :disabled="!selectedIds.length || busyDienste"
            @click="toggleSendForm('dienste')"
          >
            <EnvelopeIcon class="w-4 h-4" />
            Per E-Mail senden
          </button>
        </div>

        <div v-if="showSendForm === 'dienste'" class="flex gap-2 mt-2">
          <input
            v-model="sendEmail"
            type="email"
            placeholder="empfaenger@beispiel.de"
            class="input flex-1"
          />
          <button
            class="btn-primary"
            :disabled="!sendEmail || busyDienste"
            @click="sendPdf('dienste')"
          >
            Senden
          </button>
        </div>
        <p v-if="errorDienste" class="text-sm text-red-600 mt-2">{{ errorDienste }}</p>
      </div>

      <!-- Essensspenden-Export -->
      <div class="card">
        <h2 class="text-base font-semibold text-ink mb-1">Essensspenden</h2>
        <p class="text-sm text-muted mb-4">Spendenliste der gewählten Termine, je Spendenart eine Seite.</p>

        <div class="flex flex-wrap gap-3 mb-3">
          <button
            class="btn-secondary"
            :disabled="!selectedIds.length || busyEssen"
            @click="downloadPdf('essen')"
          >
            <ArrowDownTrayIcon class="w-4 h-4" />
            PDF herunterladen
          </button>
          <button
            class="btn-secondary"
            :disabled="!selectedIds.length || busyEssen"
            @click="toggleSendForm('essen')"
          >
            <EnvelopeIcon class="w-4 h-4" />
            Per E-Mail senden
          </button>
        </div>

        <div v-if="showSendForm === 'essen'" class="flex gap-2 mt-2">
          <input
            v-model="sendEmail"
            type="email"
            placeholder="empfaenger@beispiel.de"
            class="input flex-1"
          />
          <button
            class="btn-primary"
            :disabled="!sendEmail || busyEssen"
            @click="sendPdf('essen')"
          >
            Senden
          </button>
        </div>
        <p v-if="errorEssen" class="text-sm text-red-600 mt-2">{{ errorEssen }}</p>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDownTrayIcon, EnvelopeIcon } from '@heroicons/vue/24/outline'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const slug = computed(() => route.params.slug)

const dates = ref([])
const loadingDates = ref(true)
const selectedIds = ref([])

const showSendForm = ref(null)
const sendEmail = ref('')

const busyDienste = ref(false)
const busyEssen = ref(false)
const errorDienste = ref('')
const errorEssen = ref('')

const allSelected = computed(() => dates.value.length > 0 && selectedIds.value.length === dates.value.length)
const someSelected = computed(() => selectedIds.value.length > 0)

onMounted(async () => {
  try {
    const res = await adminApi.getDates(slug.value)
    dates.value = res.data.data
    // Default: only published dates pre-selected
    selectedIds.value = dates.value.filter(d => !d.is_draft).map(d => d.id)
  } finally {
    loadingDates.value = false
  }
})

function toggleAll(e) {
  if (e.target.checked) {
    selectedIds.value = dates.value.map(d => d.id)
  } else {
    selectedIds.value = []
  }
}

function toggleSendForm(type) {
  if (showSendForm.value === type) {
    showSendForm.value = null
  } else {
    showSendForm.value = type
    sendEmail.value = ''
  }
}

async function downloadPdf(type) {
  const busy = type === 'dienste' ? busyDienste : busyEssen
  const errRef = type === 'dienste' ? errorDienste : errorEssen
  busy.value = true
  errRef.value = ''
  try {
    const fn = type === 'dienste' ? adminApi.exportPdfDienste : adminApi.exportPdfEssen
    const res = await fn(slug.value, { date_ids: selectedIds.value })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `${type}_${slug.value}_${new Date().toISOString().slice(0, 10)}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    errRef.value = e.response?.data?.error || 'PDF-Generierung fehlgeschlagen'
  } finally {
    busy.value = false
  }
}

async function sendPdf(type) {
  const busy = type === 'dienste' ? busyDienste : busyEssen
  const errRef = type === 'dienste' ? errorDienste : errorEssen
  busy.value = true
  errRef.value = ''
  try {
    const fn = type === 'dienste' ? adminApi.sendPdfDienste : adminApi.sendPdfEssen
    await fn(slug.value, { date_ids: selectedIds.value, email: sendEmail.value })
    ui.success(`PDF an ${sendEmail.value} gesendet`)
    showSendForm.value = null
    sendEmail.value = ''
  } catch (e) {
    errRef.value = e.response?.data?.error || 'Versand fehlgeschlagen'
  } finally {
    busy.value = false
  }
}
</script>
