<template>
  <div>
    <div v-if="!instanceStore.current" class="flex justify-center py-16">
      <LoadingSpinner size="lg" />
    </div>

    <div v-else>
      <p class="text-gray-500 mb-8">
        Hallo{{ firstName ? ', ' + firstName : '' }}!
        Was möchtest du heute tun?
      </p>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <RouterLink
          :to="`/${slug}/shifts`"
          class="card p-6 flex flex-col items-center text-center hover:shadow-md transition-shadow"
        >
          <div class="w-14 h-14 rounded-full bg-primary-100 flex items-center justify-center mb-4">
            <CalendarIcon class="w-7 h-7 text-primary-600" />
          </div>
          <h2 class="text-lg font-semibold text-gray-900 mb-1">Schichten</h2>
          <p class="text-sm text-gray-500">Dienste ansehen und dich für eine Schicht einteilen</p>
        </RouterLink>

        <RouterLink
          :to="`/${slug}/food`"
          class="card p-6 flex flex-col items-center text-center hover:shadow-md transition-shadow"
        >
          <div class="w-14 h-14 rounded-full bg-primary-100 flex items-center justify-center mb-4">
            <ShoppingBagIcon class="w-7 h-7 text-primary-600" />
          </div>
          <h2 class="text-lg font-semibold text-gray-900 mb-1">Essensspende</h2>
          <p class="text-sm text-gray-500">Mitgebrachtes eintragen und die Übersicht aller Spenden sehen</p>
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useInstanceStore } from '@/stores/instance'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { CalendarIcon, ShoppingBagIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const instanceStore = useInstanceStore()

const slug = computed(() => route.params.slug)
const firstName = computed(() => auth.user?.first_name || auth.user?.name?.split(' ')[0] || '')

// Sobald Instanz-Settings geladen: direkt zu /shifts, wenn Essensspenden deaktiviert
watch(
  () => instanceStore.current,
  (settings) => {
    if (settings && !settings.food_donations_enabled) {
      router.replace(`/${slug.value}/shifts`)
    }
  },
  { immediate: true }
)
</script>
