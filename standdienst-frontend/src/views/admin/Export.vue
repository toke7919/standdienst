<template>
  <div>
    <h1 class="text-2xl font-bold text-ink mb-6">Export</h1>

    <div v-if="loadingDates" class="flex justify-center py-12">
      <LoadingSpinner size="lg" />
    </div>

    <div v-else class="grid gap-6 max-w-2xl">

      <!-- Dienste-Export -->
      <div class="card">
        <h2 class="text-base font-semibold text-ink mb-1">Dienste</h2>
        <p class="text-sm text-muted mb-3">Dienstplan der gewählten Termine, je Tag eine Seite.</p>

        <!-- Termin-Selektion Dienste -->
        <div v-if="!dienstesDates.length" class="text-sm text-muted mb-4">Keine Termine vorhanden.</div>
        <DateSelector v-else v-model="selectedDiensteIds" :dates="dienstesDates" class="mb-4" />

        <div class="flex flex-wrap gap-3 mb-3">
          <button
            class="btn-secondary"
            :disabled="!selectedDiensteIds.length || busyDienste"
            @click="downloadPdf('dienste')"
          >
            <ArrowDownTrayIcon class="w-4 h-4" />
            PDF herunterladen
          </button>
          <button
            class="btn-secondary"
            :disabled="!selectedDiensteIds.length || busyDienste"
            @click="toggleSendForm('dienste')"
          >
            <EnvelopeIcon class="w-4 h-4" />
            Per E-Mail senden
          </button>
        </div>

        <div v-if="showSendForm === 'dienste'" class="flex gap-2 mt-2">
          <input
            v-model="sendEmailDienste"
            type="email"
            placeholder="empfaenger@beispiel.de"
            class="input flex-1"
          />
          <button
            class="btn-primary"
            :disabled="!sendEmailDienste || busyDienste"
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
        <p class="text-sm text-muted mb-3">Spendenliste der gewählten Termine, je Spendenart eine Seite.</p>

        <!-- Termin-Selektion Essen -->
        <div v-if="!essenDates.length" class="text-sm text-muted mb-4">Keine Termine vorhanden.</div>
        <DateSelector v-else v-model="selectedEssenIds" :dates="essenDates" class="mb-4" />

        <div class="flex flex-wrap gap-3 mb-3">
          <button
            class="btn-secondary"
            :disabled="!selectedEssenIds.length || busyEssen"
            @click="downloadPdf('essen')"
          >
            <ArrowDownTrayIcon class="w-4 h-4" />
            PDF herunterladen
          </button>
          <button
            class="btn-secondary"
            :disabled="!selectedEssenIds.length || busyEssen"
            @click="toggleSendForm('essen')"
          >
            <EnvelopeIcon class="w-4 h-4" />
            Per E-Mail senden
          </button>
        </div>

        <div v-if="showSendForm === 'essen'" class="flex gap-2 mt-2">
          <input
            v-model="sendEmailEssen"
            type="email"
            placeholder="empfaenger@beispiel.de"
            class="input flex-1"
          />
          <button
            class="btn-primary"
            :disabled="!sendEmailEssen || busyEssen"
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
import DateSelector from '@/components/DateSelector.vue'

const route = useRoute()
const ui = useUiStore()
const slug = computed(() => route.params.slug)

const dienstesDates = ref([])
const essenDates = ref([])
const loadingDates = ref(true)
const selectedDiensteIds = ref([])
const selectedEssenIds = ref([])

const showSendForm = ref(null)   // 'dienste' | 'essen' | null
const sendEmailDienste = ref('')
const sendEmailEssen = ref('')

const busyDienste = ref(false)
const busyEssen = ref(false)
const errorDienste = ref('')
const errorEssen = ref('')

onMounted(async () => {
  try {
    const [diensteRes, essenRes] = await Promise.all([
      adminApi.getDates(slug.value, { has_shifts: 1 }),
      adminApi.getDates(slug.value, { has_food_types: 1 }),
    ])
    dienstesDates.value = diensteRes.data.data
    essenDates.value = essenRes.data.data
    selectedDiensteIds.value = dienstesDates.value.filter(d => !d.is_draft).map(d => d.id)
    selectedEssenIds.value = essenDates.value.filter(d => !d.is_draft).map(d => d.id)
  } finally {
    loadingDates.value = false
  }
})

function toggleSendForm(type) {
  showSendForm.value = showSendForm.value === type ? null : type
}

async function downloadPdf(type) {
  const busy = type === 'dienste' ? busyDienste : busyEssen
  const errRef = type === 'dienste' ? errorDienste : errorEssen
  const ids = type === 'dienste' ? selectedDiensteIds : selectedEssenIds
  busy.value = true
  errRef.value = ''
  try {
    const fn = type === 'dienste' ? adminApi.exportPdfDienste : adminApi.exportPdfEssen
    const res = await fn(slug.value, { date_ids: ids.value })
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
  const ids = type === 'dienste' ? selectedDiensteIds : selectedEssenIds
  const emailRef = type === 'dienste' ? sendEmailDienste : sendEmailEssen
  busy.value = true
  errRef.value = ''
  try {
    const fn = type === 'dienste' ? adminApi.sendPdfDienste : adminApi.sendPdfEssen
    await fn(slug.value, { date_ids: ids.value, email: emailRef.value })
    ui.success(`PDF an ${emailRef.value} gesendet`)
    showSendForm.value = null
    emailRef.value = ''
  } catch (e) {
    errRef.value = e.response?.data?.error || 'Versand fehlgeschlagen'
  } finally {
    busy.value = false
  }
}
</script>
