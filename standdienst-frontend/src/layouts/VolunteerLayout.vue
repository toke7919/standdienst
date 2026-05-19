<template>
  <!-- pb sorgt dafür, dass Inhalt nicht hinter der Bottom-Nav verschwindet -->
  <div
    class="min-h-screen flex flex-col md:pb-0"
    :class="bottomPad"
  >
    <!-- ====== HEADER ====== -->
    <header class="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-20">
      <div class="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
        <RouterLink :to="`/${slug}/shifts`" class="flex items-center gap-2 min-w-0">
          <img
            v-if="settings?.logo_filename"
            :src="`/uploads/${settings.logo_filename}`"
            class="h-8 object-contain flex-shrink-0"
            alt="Logo"
          />
          <span class="font-semibold text-gray-900 truncate">{{ settings?.site_title || 'Standdienst' }}</span>
        </RouterLink>

        <!-- Desktop-Navigation -->
        <nav class="hidden md:flex items-center gap-1">
          <RouterLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="px-3 py-1.5 text-sm rounded-lg text-gray-600 hover:bg-gray-100 transition-colors [&.router-link-active]:text-primary-700 [&.router-link-active]:font-medium"
          >{{ link.label }}</RouterLink>
          <button
            class="ml-2 px-3 py-1.5 text-sm rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
            @click="auth.logout"
          >Abmelden</button>
        </nav>
      </div>
    </header>

    <!-- ====== MAIN CONTENT ====== -->
    <main class="flex-1 max-w-4xl mx-auto w-full px-4 py-5">
      <RouterView />
    </main>

    <!-- ====== DESKTOP FOOTER ====== -->
    <footer class="hidden md:block border-t border-gray-200 bg-white mt-auto">
      <div class="max-w-4xl mx-auto px-4 py-3 flex gap-4 text-xs text-gray-400">
        <RouterLink :to="`/${slug}/impressum`" class="hover:text-gray-600">Impressum</RouterLink>
        <RouterLink :to="`/${slug}/datenschutz`" class="hover:text-gray-600">Datenschutz</RouterLink>
      </div>
    </footer>

    <!-- ====== MOBILE BOTTOM NAVIGATION ====== -->
    <nav
      class="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 z-40"
      style="padding-bottom: env(safe-area-inset-bottom, 0px)"
    >
      <div class="flex items-stretch h-[4.25rem]">
        <RouterLink
          v-for="link in bottomLinks"
          :key="link.to"
          :to="link.to"
          class="flex-1 flex flex-col items-center justify-center gap-1 text-gray-400 [&.router-link-active]:text-primary-600 transition-colors active:scale-95"
        >
          <component :is="link.icon" class="w-6 h-6" />
          <span class="text-[0.65rem] font-medium leading-none">{{ link.label }}</span>
        </RouterLink>
      </div>
    </nav>

    <ConfirmDialog />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useInstanceStore } from '@/stores/instance'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import {
  CalendarIcon, ClipboardDocumentListIcon, ShoppingBagIcon, UserCircleIcon,
} from '@heroicons/vue/24/outline'

const auth = useAuthStore()
const instanceStore = useInstanceStore()
const route = useRoute()

const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current)

// Padding-bottom für mobile: Höhe der Bottom-Nav + Safe Area
// 4.25rem = h-[4.25rem]; safe-area wird per inline-style im <nav> gesetzt,
// aber der Scrollbereich muss auch entsprechend Platz lassen.
const bottomPad = computed(() =>
  'pb-[calc(4.25rem+env(safe-area-inset-bottom,0px))]'
)

const navLinks = computed(() => {
  const s = slug.value
  const links = [{ to: `/${s}/shifts`, label: 'Schichten' }]
  if (settings.value?.shifts_enabled !== false) {
    links.push({ to: `/${s}/my-shifts`, label: 'Meine Schichten' })
  }
  if (settings.value?.food_donations_enabled) {
    links.push({ to: `/${s}/food`, label: 'Essensspende' })
  }
  links.push({ to: `/${s}/profile`, label: 'Profil' })
  return links
})

const bottomLinks = computed(() => {
  const s = slug.value
  const links = [{ to: `/${s}/shifts`, label: 'Schichten', icon: CalendarIcon }]
  if (settings.value?.shifts_enabled !== false) {
    links.push({ to: `/${s}/my-shifts`, label: 'Meine', icon: ClipboardDocumentListIcon })
  }
  if (settings.value?.food_donations_enabled) {
    links.push({ to: `/${s}/food`, label: 'Essen', icon: ShoppingBagIcon })
  }
  links.push({ to: `/${s}/profile`, label: 'Profil', icon: UserCircleIcon })
  return links
})

onMounted(() => {
  if (slug.value && !instanceStore.current) {
    instanceStore.loadInstance(slug.value)
  }
})
</script>
