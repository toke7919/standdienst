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
        <div v-if="!dates.length" class="text-sm text-muted mb-4">Keine Termine vorhanden.</div>
        <div v-else class="space-y-1.5 mb-4">
          <label class="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              :checked="allDiensteSelected"
              :indeterminate.prop="someDiensteSelected && !allDiensteSelected"
              class="rounded border-sand text-primary-600 focus:ring-primary-500"
              @change="toggleAll('dienste', $event)"
            />
            <span class="text-sm font-semibold text-ink">Alle auswählen</span>
          </label>
          <div class="border-t border-sand pt-2 space-y-1.5">
            <label v-for="d in dates" :key="d.id" class="flex items-center gap-2 cursor-pointer">
              <input
                v-model="selectedDiensteIds"
                :value="d.id"
                type="checkbox"
                class="rounded border-sand text-primary-600 focus:ring-primary-500"
              />
              <span class="text-sm text-ink">{{ d.formatted }}</span>
              <span v-if="d.label" class="text-xs text-muted">{{ d.label }}</span>
              <span
                v-if="d.is_draft"
                class="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-amber-100 text-amber-800"
              >Entwurf</span>
            </label>
          </div>
        </div>

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
        <div v-if="!dates.length" class="text-sm text-muted mb-4">Keine Termine vorhanden.</div>
        <div v-else class="space-y-1.5 mb-4">
          <label class="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              :checked="allEssenSelected"
              :indeterminate.prop="someEssenSelected && !allEssenSelected"
              class="rounded border-sand text-primary-600 focus:ring-primary-500"
              @change="toggleAll('essen', $event)"
            />
            <span class="text-sm font-semibold text-ink">Alle auswählen</span>
          </label>
          <div class="border-t border-sand pt-2 space-y-1.5">
            <label v-for="d in dates" :key="d.id" class="flex items-center gap-2 cursor-pointer">
              <input
                v-model="selectedEssenIds"
                :value="d.id"
                type="checkbox"
                class="rounded border-sand text-primary-600 focus:ring-primary-500"
              />
              <span class="text-sm text-ink">{{ d.formatted }}</span>
              <span v-if="d.label" class="text-xs text-muted">{{ d.label }}</span>
              <span
                v-if="d.is_draft"
                class="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-amber-100 text-amber-800"
              >Entwurf</span>
            </label>
          </div>
        </div>

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

const route = useRoute()
const ui = useUiStore()
const slug = computed(() => route.params.slug)

const dates = ref([])
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

const allDiensteSelected = computed(() =>
  dates.value.length > 0 && selectedDiensteIds.value.length === dates.value.length
)
const someDiensteSelected = computed(() => selectedDiensteIds.value.length > 0)
const allEssenSelected = computed(() =>
  dates.value.length > 0 && selectedEssenIds.value.length === dates.value.length
)
const someEssenSelected = computed(() => selectedEssenIds.value.length > 0)

onMounted(async () => {
  try {
    const res = await adminApi.getDates(slug.value)
    dates.value = res.data.data
    const publishedIds = dates.value.filter(d => !d.is_draft).map(d => d.id)
    selectedDiensteIds.value = [...publishedIds]
    selectedEssenIds.value = [...publishedIds]
  } finally {
    loadingDates.value = false
  }
})

function toggleAll(type, e) {
  const target = type === 'dienste' ? selectedDiensteIds : selectedEssenIds
  target.value = e.target.checked ? dates.value.map(d => d.id) : []
}

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
