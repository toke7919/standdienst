<template>
  <!-- overflow-x-clip verhindert horizontales Scrollen durch negative Margins (Home-Hero etc.) -->
  <div
    class="min-h-screen flex flex-col lg:pb-0 overflow-x-clip"
    :class="bottomPad"
  >
    <!-- ====== HEADER (fixed statt sticky – zuverlässiger auf iOS Safari) ====== -->
    <header class="bg-primary-600 shadow-sm fixed top-0 inset-x-0 z-20">
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
        <nav class="hidden lg:flex items-center gap-1">
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
            @click="auth.volunteerLogout(slug)"
          >Abmelden</button>
        </nav>
      </div>
    </header>

    <!-- Platzhalter für den fixed Header (h-14 = 3.5rem) -->
    <div class="h-14 flex-shrink-0" />

    <!-- ====== MAIN CONTENT ====== -->
    <main class="flex-1 max-w-4xl mx-auto w-full px-4 py-5">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" :key="route.path" />
        </Transition>
      </RouterView>
    </main>

    <!-- ====== DESKTOP FOOTER ====== -->
    <AppFooter class="hidden lg:block" :slug="slug" :copyright="settings?.copyright_text" />

    <!-- ====== MOBILE BOTTOM NAVIGATION ====== -->
    <nav
      class="lg:hidden fixed bottom-0 inset-x-0 bg-soft border-t border-sand z-40"
      style="padding-bottom: env(safe-area-inset-bottom, 0px)"
    >
      <div class="flex items-stretch h-[4.25rem]">
        <RouterLink
          v-for="link in bottomLinks"
          :key="link.to"
          :to="link.to"
          class="relative flex-1 flex flex-col items-center justify-center gap-1 text-muted [&.router-link-active]:text-primary-600 transition-all duration-150 active:scale-90"
        >
          <span class="absolute top-0 inset-x-2 h-[3px] rounded-b-full bg-primary-600 scale-x-0 [.router-link-active_&]:scale-x-100 transition-transform duration-200 origin-center" />
          <component :is="link.icon" class="w-6 h-6 transition-transform duration-150 [.router-link-active_&]:scale-110" />
          <span class="text-[0.65rem] font-medium leading-none">{{ link.label }}</span>
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
import { isColorDark, applyTheme } from '@/utils/colorPalette'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import AppFooter from '@/components/AppFooter.vue'
import {
  CalendarIcon, ClipboardDocumentListIcon, ShoppingBagIcon, UserCircleIcon,
} from '@heroicons/vue/24/outline'

const auth = useAuthStore()
const instanceStore = useInstanceStore()
const route = useRoute()

const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current)

const headerTextClass = computed(() => {
  const color = settings.value?.primary_color || '#7c3aed'
  return isColorDark(color) ? 'text-white' : 'text-ink'
})

// Padding-bottom für mobile: Höhe der Bottom-Nav + Safe Area
const bottomPad = computed(() =>
  'pb-[calc(4.25rem+env(safe-area-inset-bottom,0px))]'
)

const navLinks = computed(() => {
  const s = slug.value
  const links = [{ to: `/${s}/shifts`, label: 'Dienste' }]
  if (settings.value?.shifts_enabled !== false) {
    links.push({ to: `/${s}/my-shifts`, label: 'Meine Dienste' })
  }
  if (settings.value?.food_donations_enabled) {
    links.push({ to: `/${s}/food`, label: 'Essensspende' })
  }
  links.push({ to: `/${s}/profile`, label: 'Profil' })
  return links
})

const bottomLinks = computed(() => {
  const s = slug.value
  const links = [{ to: `/${s}/shifts`, label: 'Dienste', icon: CalendarIcon }]
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
  if (s?.primary_color) applyTheme(s.primary_color)
  updateFavicon(s?.logo_filename || null, s?.primary_color || null)
}, { immediate: true })

function updateFavicon(logoFilename, primaryColor) {
  const logoUrl = logoFilename ? `/uploads/${logoFilename}` : null

  // Favicon + Apple Touch Icon
  for (const rel of ['icon', 'apple-touch-icon']) {
    let link = document.querySelector(`link[rel="${rel}"]`)
    if (logoUrl) {
      if (!link) {
        link = document.createElement('link')
        link.rel = rel
        document.head.appendChild(link)
      }
      link.href = logoUrl
    } else if (link && rel !== 'icon') {
      // Nur dynamisch hinzugefügte entfernen; den Standard-favicon.svg aus index.html behalten
      link.remove()
    }
  }

  // Theme-Color (Browser-Chrome-Farbe auf mobil)
  let meta = document.querySelector('meta[name="theme-color"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'theme-color'
    document.head.appendChild(meta)
  }
  meta.content = primaryColor || '#4f46e5'

  // iOS Web-App-Titel
  let appTitle = document.querySelector('meta[name="apple-mobile-web-app-title"]')
  if (!appTitle) {
    appTitle = document.createElement('meta')
    appTitle.name = 'apple-mobile-web-app-title'
    document.head.appendChild(appTitle)
  }
  appTitle.content = document.title
}
</script>

<style scoped>
.page-enter-active { transition: opacity 0.12s ease; }
.page-leave-active { transition: opacity 0.08s ease; }
.page-enter-from, .page-leave-to { opacity: 0; }
</style>
