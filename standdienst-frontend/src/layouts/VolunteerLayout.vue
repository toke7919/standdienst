<template>
  <!-- pb sorgt dafür, dass Inhalt nicht hinter der Bottom-Nav verschwindet -->
  <div
    class="min-h-screen flex flex-col md:pb-0"
    :class="bottomPad"
  >
    <!-- ====== HEADER ====== -->
    <header class="bg-primary-600 shadow-sm sticky top-0 z-20">
      <div class="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
        <RouterLink :to="`/${slug}`" class="flex items-center gap-2 min-w-0">
          <img
            v-if="settings?.logo_filename"
            :src="`/uploads/${settings.logo_filename}`"
            class="h-8 object-contain flex-shrink-0"
            alt="Logo"
          />
          <span class="font-semibold truncate" :class="headerTextClass">
            {{ settings?.site_title || 'Standdienst' }}
          </span>
        </RouterLink>

        <!-- Desktop-Navigation -->
        <nav class="hidden md:flex items-center gap-1">
          <RouterLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="px-3 py-1.5 text-sm rounded-lg transition-colors [&.router-link-active]:font-semibold"
            :class="headerTextClass + ' hover:bg-white/20 [&.router-link-active]:bg-white/20'"
          >{{ link.label }}</RouterLink>
          <button
            class="ml-2 px-3 py-1.5 text-sm rounded-lg hover:bg-white/20 transition-colors"
            :class="headerTextClass"
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
          class="flex-1 flex flex-col items-center justify-center gap-1 text-gray-400 [&.router-link-active]:text-primary-600 transition-all duration-150 active:scale-90"
        >
          <component :is="link.icon" class="w-6 h-6 transition-transform duration-150 [.router-link-active_&]:scale-110" />
          <span class="text-[0.65rem] font-medium leading-none">{{ link.label }}</span>
          <span class="w-1 h-1 rounded-full bg-primary-600 opacity-0 [.router-link-active_&]:opacity-100 transition-opacity duration-150" />
        </RouterLink>
      </div>
    </nav>

    <ConfirmDialog />
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useInstanceStore } from '@/stores/instance'
import { isColorDark } from '@/utils/colorPalette'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import {
  CalendarIcon, ClipboardDocumentListIcon, ShoppingBagIcon, UserCircleIcon,
} from '@heroicons/vue/24/outline'

const auth = useAuthStore()
const instanceStore = useInstanceStore()
const route = useRoute()

const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current)

const headerTextClass = computed(() => {
  const color = settings.value?.primary_color || '#4f46e5'
  return isColorDark(color) ? 'text-white' : 'text-gray-900'
})

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
  if (slug.value) instanceStore.loadInstance(slug.value)
})

watch(settings, (s) => {
  if (s?.site_title) document.title = s.site_title
})
</script>
