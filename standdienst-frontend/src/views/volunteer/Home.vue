<template>
  <div>
    <div v-if="!instanceStore.current" class="flex justify-center py-16">
      <LoadingSpinner size="lg" />
    </div>

    <div v-else>
      <!-- Hero-Streifen (hebt Layout-Padding auf, füllt bis zur Kante) -->
      <div class="-mx-4 -mt-5 bg-linear-to-br from-primary-600 to-primary-900 px-6 pt-12 pb-20 text-white">
        <p class="text-primary-300 text-sm font-medium mb-1">{{ greeting }}</p>
        <h1 class="text-2xl font-bold tracking-tight">
          <span v-if="firstName">{{ firstName }}</span>
          <span v-else>Willkommen!</span>
        </h1>
        <p class="text-primary-200 mt-1 text-sm">Was möchtest du heute tun?</p>
      </div>

      <!-- Aktionskacheln (überlappen den Hero) -->
      <div class="relative z-10 -mt-12 space-y-3">

        <RouterLink :to="`/${slug}/shifts`" class="card-interactive block">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-md bg-primary-100 flex items-center justify-center shrink-0
                        transition-colors duration-150 group-hover:bg-primary-200">
              <CalendarIcon class="w-6 h-6 text-primary-600" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-ink">Dienste</p>
              <p class="text-sm text-muted mt-0.5">Dienste ansehen und dich einteilen</p>
            </div>
            <ChevronRightIcon class="w-5 h-5 text-sand shrink-0" />
          </div>
        </RouterLink>

        <RouterLink :to="`/${slug}/food`" class="card-interactive block">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-md bg-primary-100 flex items-center justify-center shrink-0 transition-colors duration-150">
              <ShoppingBagIcon class="w-6 h-6 text-primary-600" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-ink">Essensspende</p>
              <p class="text-sm text-muted mt-0.5">Mitgebrachtes eintragen und Übersicht ansehen</p>
            </div>
            <ChevronRightIcon class="w-5 h-5 text-sand shrink-0" />
          </div>
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
import { CalendarIcon, ShoppingBagIcon, ChevronRightIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const instanceStore = useInstanceStore()

const slug = computed(() => route.params.slug)
const firstName = computed(() => auth.user?.first_name || auth.user?.name?.split(' ')[0] || '')

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 11) return 'Guten Morgen'
  if (h < 17) return 'Hallo'
  return 'Guten Abend'
})

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
