<template>
  <div>
    <h1 class="text-xl font-bold text-gray-900 mb-6">Essensspende</h1>

    <div class="card mb-6">
      <h2 class="text-base font-semibold text-gray-800 mb-4">Spende anmelden</h2>
      <form @submit.prevent="add" class="space-y-3">
        <div>
          <label class="label">Kategorie</label>
          <select v-model="form.food_type_id" class="input" required>
            <option value="">Bitte wählen</option>
            <option v-for="t in foodTypes" :key="t.id" :value="t.id">
              {{ t.name }} (noch {{ t.spots_left }} verfügbar)
            </option>
          </select>
        </div>
        <div>
          <label class="label">Menge</label>
          <input v-model.number="form.quantity" type="number" min="1" class="input max-w-32" required />
        </div>
        <p v-if="errorMsg" class="text-sm text-red-600">{{ errorMsg }}</p>
        <button type="submit" class="btn-primary" :disabled="loading">Anmelden</button>
      </form>
    </div>

    <div class="card">
      <h2 class="text-base font-semibold text-gray-800 mb-4">Meine Spenden</h2>
      <div class="space-y-2">
        <div
          v-for="d in myDonations"
          :key="d.id"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
        >
          <div>
            <p class="font-medium text-gray-900">{{ d.food_type_name }}</p>
            <p class="text-sm text-gray-500">Menge: {{ d.quantity }}</p>
          </div>
          <button class="text-sm text-red-600 hover:underline" @click="remove(d)">Entfernen</button>
        </div>
        <p v-if="!myDonations.length" class="text-center text-gray-400 py-4">Noch keine Spenden</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { volunteerApi } from '@/api/volunteer'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const ui = useUiStore()
const foodTypes = ref([])
const myDonations = ref([])
const form = ref({ food_type_id: '', quantity: 1 })
const loading = ref(false)
const errorMsg = ref('')

onMounted(load)

async function load() {
  const [tRes, dRes] = await Promise.all([
    adminApi.getFoodTypes(route.params.slug),
    volunteerApi.getFoodDonations(route.params.slug),
  ])
  foodTypes.value = tRes.data.data
  myDonations.value = dRes.data.data
}

async function add() {
  loading.value = true
  errorMsg.value = ''
  try {
    await volunteerApi.addFoodDonation(route.params.slug, form.value)
    ui.success('Spende angemeldet')
    form.value = { food_type_id: '', quantity: 1 }
    await load()
  } catch (e) {
    errorMsg.value = e.response?.data?.error || 'Fehler'
  } finally {
    loading.value = false
  }
}

async function remove(d) {
  const ok = await ui.confirm({ title: 'Spende entfernen', message: 'Spende entfernen?', danger: true })
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
