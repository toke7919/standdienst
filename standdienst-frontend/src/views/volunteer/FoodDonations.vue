<template>
  <div>
    <h1 class="text-xl font-bold text-ink mb-6">Essensspende</h1>

    <!-- Skeleton -->
    <div v-if="!loaded" class="space-y-6">
      <div v-for="i in 2" :key="i" class="card overflow-hidden p-0!">
        <div class="h-1 bg-sand rounded-t-md" />
        <div class="p-6 space-y-3">
          <div class="h-4 w-40 bg-bg-warm rounded-sm animate-pulse" />
          <div class="h-3 w-56 bg-bg-warm rounded-sm animate-pulse" />
          <div class="border-t border-sand my-1" />
          <div class="h-10 bg-bg-warm rounded-lg animate-pulse" />
          <div class="h-8 w-24 bg-bg-warm rounded-lg animate-pulse" />
        </div>
      </div>
    </div>

    <p v-else-if="!combinedTypes.length" class="text-center text-muted py-8">
      Noch keine Spendenkategorien vorhanden
    </p>

    <div v-else class="space-y-6">
      <div v-for="t in combinedTypes" :key="t.id" class="card overflow-hidden p-0!">
        <!-- farbiger Streifen oben -->
        <div class="h-1 bg-primary-500 rounded-t-md" />

        <div class="p-6">
        <!-- Typ-Kopf: Name -->
        <div class="mb-1">
          <h2 class="text-base font-semibold text-ink">{{ t.name }}</h2>
        </div>

        <!-- Abgabe-Info -->
        <p v-if="t.delivery_datetime || t.delivery_location" class="text-sm text-primary-700 font-medium mb-3">
          {{ deliveryText(t) }}
        </p>

        <!-- Hinweistext -->
        <p v-if="t.notes" class="text-sm text-muted italic mb-3">{{ t.notes }}</p>

        <div class="border-t border-sand my-3" />

        <!-- Eintragungs-Formular -->
        <form @submit.prevent="add(t.id)" class="space-y-2">
          <input
            v-model="forms[t.id].description"
            class="input"
            required
            maxlength="100"
            placeholder="Was bringst du mit? z. B. Bananenkuchen …"
          />
          <div v-if="t.refrigeration_enabled" class="flex items-center gap-2">
            <input v-model="forms[t.id].needs_refrigeration" type="checkbox" :id="`ref-${t.id}`" />
            <label :for="`ref-${t.id}`" class="text-sm text-ink/80">Kühlung erforderlich</label>
          </div>
          <p v-if="errors[t.id]" class="text-sm text-red-600">{{ errors[t.id] }}</p>
          <button type="submit" class="btn-primary text-sm" :disabled="submitting === t.id">
            <LoadingSpinner v-if="submitting === t.id" size="sm" class="mr-1" />
            Eintragen
          </button>
        </form>

        <!-- Vorhandene Spenden -->
        <div class="border-t border-sand mt-4 pt-3">

          <!-- Eigene Spenden: immer sichtbar -->
          <div v-if="t.myDonations.length" class="space-y-2" :class="t.otherDonations.length ? 'mb-3' : ''">
            <div
              v-for="d in t.myDonations"
              :key="d.id"
              class="flex items-center justify-between rounded-xl px-3 py-2.5 gap-3 border bg-primary-50 border-primary-200"
            >
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-primary-700 truncate">
                  {{ d.description }}
                  <span v-if="d.needs_refrigeration" class="ml-1 text-sky-400" title="Kühlung erforderlich">❄</span>
                </p>
                <p class="text-xs text-muted mt-0.5 truncate">{{ d.volunteer_name }}</p>
              </div>
              <button
                class="shrink-0 text-sand hover:text-red-500 transition-colors"
                title="Entfernen"
                @click="remove(d)"
              >
                <XMarkIcon class="w-4 h-4" />
              </button>
            </div>
          </div>

          <!-- Fremde Spenden: einklappbar -->
          <template v-if="t.otherDonations.length">
            <button
              type="button"
              class="flex items-center justify-between w-full text-left gap-2"
              @click="donationsOpen[t.id] = !donationsOpen[t.id]"
            >
              <span class="text-xs text-muted font-medium">
                {{ t.otherDonations.length }}
                {{ t.myDonations.length ? 'weitere' : '' }}
                {{ t.otherDonations.length === 1 ? 'Eintragung' : 'Eintragungen' }}
              </span>
              <ChevronDownIcon
                class="w-3.5 h-3.5 text-muted shrink-0 transition-transform duration-200"
                :class="donationsOpen[t.id] ? '' : '-rotate-90'"
              />
            </button>
            <div v-if="donationsOpen[t.id]" class="mt-2 space-y-2">
              <div
                v-for="d in t.otherDonations"
                :key="d.id"
                class="flex items-center rounded-xl px-3 py-2.5 gap-3 border bg-bg-brand border-transparent"
              >
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-ink truncate">
                    {{ d.description }}
                    <span v-if="d.needs_refrigeration" class="ml-1 text-sky-400" title="Kühlung erforderlich">❄</span>
                  </p>
                  <p class="text-xs text-muted mt-0.5 truncate">{{ d.volunteer_name }}</p>
                </div>
              </div>
            </div>
          </template>

          <!-- Leerzustand -->
          <p v-if="!t.donations.length" class="text-xs text-muted">Noch keine Eintragungen</p>
        </div>

        </div><!-- /p-6 -->
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { volunteerApi } from '@/api/volunteer'
import { useUiStore } from '@/stores/ui'
import { XMarkIcon, ChevronDownIcon } from '@heroicons/vue/24/outline'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const foodTypes = ref([])
const grouped = ref([])
const forms = ref({})
const errors = ref({})
const donationsOpen = ref({})
const submitting = ref(null)
const loaded = ref(false)

const combinedTypes = computed(() =>
  foodTypes.value
    .map(t => {
      const group = grouped.value.find(g => g.id === t.id)
      const donations = group?.donations || []
      return {
        ...t,
        donations,
        myDonations: donations.filter(d => d.is_mine),
        otherDonations: donations.filter(d => !d.is_mine).sort((a, b) => (a.description || '').localeCompare(b.description || '', 'de')),
      }
    })
    .sort((a, b) => {
      if (!a.delivery_datetime && !b.delivery_datetime) return 0
      if (!a.delivery_datetime) return 1
      if (!b.delivery_datetime) return -1
      return new Date(a.delivery_datetime) - new Date(b.delivery_datetime)
    })
)

onMounted(load)

async function load() {
  const [tRes, dRes] = await Promise.all([
    volunteerApi.getFoodTypes(route.params.slug),
    volunteerApi.getFoodDonations(route.params.slug),
  ])
  foodTypes.value = tRes.data.data
  grouped.value = dRes.data.data
  for (const t of foodTypes.value) {
    if (!forms.value[t.id]) forms.value[t.id] = { description: '', needs_refrigeration: false }
    if (errors.value[t.id] === undefined) errors.value[t.id] = ''
    if (donationsOpen.value[t.id] === undefined) donationsOpen.value[t.id] = false
  }
  loaded.value = true
}

async function add(typeId) {
  errors.value[typeId] = ''
  submitting.value = typeId
  try {
    await volunteerApi.addFoodDonation(route.params.slug, {
      food_type_id: typeId,
      description: forms.value[typeId].description,
      needs_refrigeration: forms.value[typeId].needs_refrigeration,
    })
    ui.success('Spende angemeldet')
    forms.value[typeId] = { description: '', needs_refrigeration: false }
    await load()
  } catch (e) {
    errors.value[typeId] = e.response?.data?.error || 'Fehler'
  } finally {
    submitting.value = null
  }
}

async function remove(d) {
  const ok = await ui.confirm({ title: 'Spende entfernen', message: 'Spende wirklich entfernen?', danger: true })
  if (!ok) return
  try {
    await volunteerApi.removeFoodDonation(route.params.slug, d.id)
    ui.success('Entfernt')
    await load()
  } catch (e) {
    ui.err(e.response?.data?.error || 'Fehler')
  }
}

function fmtDt(iso) {
  return iso ? new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' }) : ''
}

function deliveryText(t) {
  const time = t.delivery_datetime ? fmtDt(t.delivery_datetime) : null
  const loc = t.delivery_location || null
  if (time && loc) return `Bitte am ${time} bei ${loc} abgeben.`
  if (time) return `Bitte am ${time} abgeben.`
  return `Bitte am/bei ${loc} abgeben.`
}
</script>
