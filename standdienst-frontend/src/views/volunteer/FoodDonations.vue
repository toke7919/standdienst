<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 mb-6">Essensspende</h1>

    <p v-if="loaded && !combinedTypes.length" class="text-center text-gray-400 py-8">
      Noch keine Spendenkategorien vorhanden
    </p>

    <div class="space-y-6">
      <div v-for="t in combinedTypes" :key="t.id" class="card">

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
        <div v-if="t.donations.length" class="border-t border-gray-100 mt-4 pt-3 space-y-1.5">
          <div
            v-for="d in t.donations"
            :key="d.id"
            class="flex items-center justify-between text-sm"
          >
            <span :class="d.is_mine ? 'text-primary-700 font-medium' : 'text-gray-700'">
              {{ d.description }}
              <span class="font-normal text-gray-500"> ({{ d.volunteer_name }})</span>
              <span
                v-if="d.needs_refrigeration"
                class="ml-1.5 text-xs bg-blue-100 text-blue-700 rounded px-1.5 py-0.5"
              >Kühlung</span>
            </span>
            <button
              v-if="d.is_mine"
              class="ml-3 text-xs text-red-600 hover:underline flex-shrink-0"
              @click="remove(d)"
            >Entfernen</button>
          </div>
        </div>
        <p v-else class="border-t border-gray-100 mt-4 pt-3 text-xs text-gray-400">
          Noch keine Eintragungen
        </p>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { volunteerApi } from '@/api/volunteer'
import { useUiStore } from '@/stores/ui'
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
