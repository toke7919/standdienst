<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 mb-6">Essensspende</h1>

    <!-- Skeleton -->
    <div v-if="!loaded" class="space-y-6">
      <div v-for="i in 2" :key="i" class="card overflow-hidden !p-0">
        <div class="h-1 bg-gray-200 rounded-t-2xl" />
        <div class="p-6 space-y-3">
          <div class="h-4 w-40 bg-gray-100 rounded animate-pulse" />
          <div class="h-3 w-56 bg-gray-100 rounded animate-pulse" />
          <div class="border-t border-gray-100 my-1" />
          <div class="h-10 bg-gray-100 rounded-lg animate-pulse" />
          <div class="h-8 w-24 bg-gray-100 rounded-lg animate-pulse" />
        </div>
      </div>
    </div>

    <p v-else-if="!combinedTypes.length" class="text-center text-gray-400 py-8">
      Noch keine Spendenkategorien vorhanden
    </p>

    <div v-else class="space-y-6">
      <div v-for="t in combinedTypes" :key="t.id" class="card overflow-hidden !p-0">
        <!-- farbiger Streifen oben -->
        <div class="h-1 bg-primary-500 rounded-t-2xl" />

        <div class="p-6">
        <!-- Typ-Kopf: Name + Zähler -->
        <div class="flex items-start justify-between mb-1">
          <h2 class="text-base font-semibold text-gray-900">{{ t.name }}</h2>
          <span class="text-xs text-gray-400 mt-0.5 ml-2 flex-shrink-0">
            {{ t.donations.length }} {{ t.donations.length === 1 ? 'Eintragung' : 'Eintragungen' }}
          </span>
        </div>

        <!-- Abgabe-Info -->
        <p v-if="t.delivery_datetime || t.delivery_location" class="text-sm text-gray-500 mb-1">
          <span v-if="t.delivery_datetime">Abgabe: {{ fmtDt(t.delivery_datetime) }}</span>
          <span v-if="t.delivery_datetime && t.delivery_location"> · </span>
          <span v-if="t.delivery_location">{{ t.delivery_location }}</span>
        </p>

        <!-- Hinweistext -->
        <p v-if="t.notes" class="text-sm text-gray-500 italic mb-3">{{ t.notes }}</p>

        <div class="border-t border-gray-100 my-3" />

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
            <label :for="`ref-${t.id}`" class="text-sm text-gray-700">Kühlung erforderlich</label>
          </div>
          <p v-if="errors[t.id]" class="text-sm text-red-600">{{ errors[t.id] }}</p>
          <button type="submit" class="btn-primary text-sm" :disabled="submitting === t.id">
            <LoadingSpinner v-if="submitting === t.id" size="sm" class="mr-1" />
            Eintragen
          </button>
        </form>

        <!-- Vorhandene Spenden alphabetisch -->
        <div v-if="t.donations.length" class="border-t border-gray-100 mt-4 pt-3 space-y-2">
          <div
            v-for="d in t.donations"
            :key="d.id"
            class="flex items-center justify-between rounded-xl px-3 py-2.5 gap-3 border"
            :class="d.is_mine ? 'bg-primary-50 border-primary-200' : 'bg-gray-50 border-transparent'"
          >
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium truncate" :class="d.is_mine ? 'text-primary-700' : 'text-gray-800'">
                {{ d.description }}
                <span
                  v-if="d.needs_refrigeration"
                  class="ml-1 text-sky-400"
                  title="Kühlung erforderlich"
                >❄</span>
              </p>
              <p class="text-xs text-gray-400 mt-0.5 truncate">{{ d.volunteer_name }}</p>
            </div>
            <button
              v-if="d.is_mine"
              class="flex-shrink-0 text-gray-300 hover:text-red-500 transition-colors"
              title="Entfernen"
              @click="remove(d)"
            >
              <XMarkIcon class="w-4 h-4" />
            </button>
          </div>
        </div>
        <p v-else class="border-t border-gray-100 mt-4 pt-3 text-xs text-gray-400">
          Noch keine Eintragungen
        </p>

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
import { XMarkIcon } from '@heroicons/vue/24/outline'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const foodTypes = ref([])
const grouped = ref([])
const forms = ref({})
const errors = ref({})
const submitting = ref(null)
const loaded = ref(false)

const combinedTypes = computed(() =>
  foodTypes.value.map(t => {
    const group = grouped.value.find(g => g.id === t.id)
    return { ...t, donations: group?.donations || [] }
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
</script>
