<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 mb-6">Essensspende</h1>

    <!-- Formular: Neue Spende anmelden -->
    <div class="card mb-6">
      <h2 class="text-base font-semibold text-gray-800 mb-4">Spende anmelden</h2>
      <form @submit.prevent="add" class="space-y-3">
        <div>
          <label class="label">Was bringst du mit? <span class="text-red-500">*</span></label>
          <input v-model="form.description" class="input" required maxlength="100"
                 placeholder="z.B. Bananenkuchen, 2 Liter Orangensaft …" />
        </div>
        <div>
          <label class="label">Kategorie <span class="text-red-500">*</span></label>
          <select v-model="form.food_type_id" class="input" required>
            <option value="">Bitte wählen</option>
            <option v-for="t in foodTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>
        <div v-if="refrigerationEnabled" class="flex items-center gap-2">
          <input v-model="form.needs_refrigeration" type="checkbox" id="refrigeration" />
          <label for="refrigeration" class="text-sm text-gray-700">Kühlung erforderlich</label>
        </div>
        <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
        <button type="submit" class="btn-primary" :disabled="loading">
          <LoadingSpinner v-if="loading" size="sm" class="mr-1" />
          Anmelden
        </button>
      </form>
    </div>

    <!-- Alle Spenden je Kategorie -->
    <div v-if="grouped.length" class="space-y-4">
      <div v-for="group in grouped" :key="group.id" class="card">
        <h2 class="text-base font-semibold text-gray-800 mb-3">{{ group.name }}</h2>
        <div class="space-y-2">
          <div
            v-for="d in group.donations"
            :key="d.id"
            class="flex items-center justify-between rounded-lg px-3 py-2"
            :class="d.is_mine ? 'bg-primary-50 border border-primary-200' : 'bg-gray-50'"
          >
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-gray-900 truncate">{{ d.description }}</p>
              <div class="flex items-center gap-2 mt-0.5">
                <span class="text-xs text-gray-500">{{ d.volunteer_name }}</span>
                <span v-if="d.needs_refrigeration"
                      class="text-xs bg-blue-100 text-blue-700 rounded-full px-1.5 py-0.5">
                  Kühlung
                </span>
              </div>
            </div>
            <button v-if="d.is_mine"
                    class="ml-3 text-xs text-red-600 hover:underline flex-shrink-0"
                    @click="remove(d)">
              Entfernen
            </button>
          </div>
        </div>
        <p v-if="!group.donations.length" class="text-sm text-gray-400 py-2">
          Noch keine Spenden in dieser Kategorie
        </p>
      </div>
    </div>
    <p v-else-if="loaded" class="text-center text-gray-400 py-8">Noch keine Spendenkategorien vorhanden</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useInstanceStore } from '@/stores/instance'
import { volunteerApi } from '@/api/volunteer'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const route = useRoute()
const ui = useUiStore()
const instanceStore = useInstanceStore()
const foodTypes = ref([])
const grouped = ref([])
const form = ref({ food_type_id: '', description: '', needs_refrigeration: false })
const loading = ref(false)
const loaded = ref(false)
const errorMsg = ref('')

const refrigerationEnabled = computed(
  () => foodTypes.value.find(t => t.id === form.value.food_type_id)?.refrigeration_enabled ?? false
)

onMounted(load)

async function load() {
  const [tRes, dRes] = await Promise.all([
    volunteerApi.getFoodTypes(route.params.slug),
    volunteerApi.getFoodDonations(route.params.slug),
  ])
  foodTypes.value = tRes.data.data
  grouped.value = dRes.data.data
  loaded.value = true
}

async function add() {
  loading.value = true
  errorMsg.value = ''
  try {
    await volunteerApi.addFoodDonation(route.params.slug, {
      food_type_id: form.value.food_type_id,
      description: form.value.description,
      needs_refrigeration: refrigerationEnabled.value ? form.value.needs_refrigeration : false,
    })
    ui.success('Spende angemeldet')
    form.value = { food_type_id: '', description: '', needs_refrigeration: false }
    await load()
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Fehler'
  } finally {
    loading.value = false
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
</script>
