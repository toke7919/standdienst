<template>
  <div class="min-h-screen bg-gray-50 flex">

    <!-- ============================= DESKTOP SIDEBAR ============================= -->
    <aside class="hidden md:flex flex-col bg-primary-950 w-64 fixed inset-y-0 z-40">
      <div class="p-5 border-b border-white/10 flex items-center gap-2">
        <RouterLink :to="selectedSlug ? `/admin/${selectedSlug}/dashboard` : '/admin/dashboard'" class="flex items-center gap-2 min-w-0">
          <img
            v-if="instanceInfo?.logo_filename"
            :src="`/uploads/${instanceInfo.logo_filename}`"
            class="h-8 w-8 object-contain rounded-lg flex-shrink-0"
            alt="Logo"
          />
          <div v-else class="w-8 h-8 bg-white/15 rounded-lg flex items-center justify-center flex-shrink-0 border border-white/20">
            <span class="text-white text-sm font-bold">{{ instanceInitial }}</span>
          </div>
          <span class="font-semibold text-white truncate">{{ instanceInfo?.site_title || 'Standdienst' }}</span>
        </RouterLink>
      </div>

      <div v-if="auth.isLoggedIn" class="p-3 border-b border-white/10">
        <select v-model="selectedSlug" class="w-full text-sm text-white bg-white/10 border border-white/20 rounded-lg px-3 py-2 cursor-pointer focus:outline-none focus:ring-1 focus:ring-white/30 appearance-none" @change="onInstanceChange">
          <option value="" class="text-gray-900 bg-white">Plattform</option>
          <option v-for="inst in instances" :key="inst.id" :value="inst.slug" class="text-gray-900 bg-white">{{ inst.name }}</option>
        </select>
      </div>

      <nav class="flex-1 overflow-y-auto p-3 space-y-0.5">
        <NavItem :to="selectedSlug ? `/admin/${selectedSlug}/dashboard` : '/admin/dashboard'" :icon="HomeIcon">Dashboard</NavItem>

        <template v-if="selectedSlug">
          <p class="px-3 pt-4 pb-1 text-[10px] font-semibold text-white/35 uppercase tracking-widest">Instanz</p>
          <NavItem :to="`/admin/${selectedSlug}/volunteers`" :icon="UsersIcon">Helfer</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/stands`" :icon="BuildingStorefrontIcon">Stände</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/dates`" :icon="CalendarIcon">Termine</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/shifts`" :icon="ClockIcon">Schichten</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/registrations`" :icon="ClipboardDocumentListIcon">Anmeldungen</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/food`" :icon="ShoppingBagIcon">Essensspenden</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/export`" :icon="ArrowDownTrayIcon">Export</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/import`" :icon="ArrowUpTrayIcon">Import</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/settings`" :icon="CogIcon">Einstellungen</NavItem>
          <NavItem v-if="auth.isInstanceAdmin" :to="`/admin/${selectedSlug}/activity`" :icon="DocumentTextIcon">Protokoll</NavItem>
        </template>

        <template v-if="auth.isAdmin && !selectedSlug">
          <p class="px-3 pt-4 pb-1 text-[10px] font-semibold text-white/35 uppercase tracking-widest">Plattform</p>
          <NavItem to="/admin/instances" :icon="ServerIcon">Instanzen</NavItem>
          <NavItem to="/admin/organizers" :icon="UserGroupIcon">Organisatoren</NavItem>
          <NavItem to="/admin/admins" :icon="ShieldCheckIcon">Admins</NavItem>
          <NavItem to="/admin/settings/global" :icon="AdjustmentsHorizontalIcon">Globale Einst.</NavItem>
          <NavItem to="/admin/settings/mail" :icon="EnvelopeIcon">Mail-Einst.</NavItem>
          <NavItem to="/admin/activity" :icon="DocumentTextIcon">Globales Protokoll</NavItem>
          <NavItem to="/admin/backup" :icon="CloudArrowUpIcon">Backup</NavItem>
          <NavItem to="/admin/update" :icon="ArrowPathIcon">Update</NavItem>
        </template>
      </nav>

      <div class="p-3 border-t border-white/10 space-y-0.5">
        <NavItem to="/admin/profile/2fa" :icon="LockClosedIcon">2FA einrichten</NavItem>
        <NavItem to="/admin/profile/passkeys" :icon="KeyIcon">Passkeys</NavItem>
        <button
          class="w-full flex items-center gap-2 px-3 py-2 text-sm text-white/60 hover:bg-white/10 hover:text-white rounded-lg transition-colors"
          @click="auth.logout"
        >
          <ArrowRightOnRectangleIcon class="w-4 h-4" />
          Abmelden
        </button>
      </div>
    </aside>

    <!-- ============================= MOBILE HEADER ============================= -->
    <header class="md:hidden fixed top-0 inset-x-0 z-30 bg-primary-950 border-b border-white/10 h-14 flex items-center px-4 gap-3">
      <div class="flex items-center gap-2 flex-1 min-w-0">
        <img
          v-if="instanceInfo?.logo_filename"
          :src="`/uploads/${instanceInfo.logo_filename}`"
          class="h-7 w-7 object-contain rounded-md flex-shrink-0"
          alt="Logo"
        />
        <div v-else class="w-7 h-7 bg-white/15 rounded-md flex items-center justify-center flex-shrink-0 border border-white/20">
          <span class="text-white text-xs font-bold">{{ instanceInitial }}</span>
        </div>
        <span class="font-semibold text-white text-sm truncate">
          {{ instanceInfo?.site_title || (mobileSlug ? (instances.find(i => i.slug === mobileSlug)?.name || mobileSlug) : 'Admin') }}
        </span>
      </div>
      <!-- Instanz-Selektor im Header -->
      <select
        v-if="auth.isLoggedIn && instances.length > 1"
        v-model="selectedSlug"
        class="text-xs border border-white/20 rounded-lg px-2 py-1.5 bg-white/10 text-white max-w-[9rem] flex-shrink-0 focus:outline-none"
        @change="onInstanceChange"
      >
        <option value="" class="text-gray-900 bg-white">Plattform</option>
        <option v-for="inst in instances" :key="inst.id" :value="inst.slug" class="text-gray-900 bg-white">{{ inst.name }}</option>
      </select>
    </header>

    <!-- ============================= MAIN CONTENT ============================= -->
    <div
      class="flex-1 md:ml-64 flex flex-col min-h-screen"
      :class="mobileContentPad"
    >
      <main class="flex-1 p-4 md:p-6">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" :key="route.path" />
          </Transition>
        </RouterView>
      </main>
    </div>

    <!-- ============================= MOBILE BOTTOM NAV ============================= -->
    <nav
      class="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-gray-200"
      style="padding-bottom: env(safe-area-inset-bottom, 0px)"
    >
      <div class="flex items-stretch h-[4.25rem]">
        <!-- Dashboard -->
        <RouterLink
          :to="mobileSlug ? `/admin/${mobileSlug}/dashboard` : '/admin/dashboard'"
          class="relative flex-1 flex flex-col items-center justify-center gap-1 text-gray-400 transition-colors active:scale-95"
          :class="isTabActive('dashboard') ? 'text-primary-600' : ''"
          @click="moreOpen = false"
        >
          <span class="absolute top-0 inset-x-2 h-[3px] rounded-b-full bg-primary-600 transition-transform duration-200 origin-center" :class="isTabActive('dashboard') ? 'scale-x-100' : 'scale-x-0'" />
          <HomeIcon class="w-6 h-6" />
          <span class="text-[0.65rem] font-medium leading-none">Dashboard</span>
        </RouterLink>

        <!-- Tab 2: Helfer (Instanz) oder Instanzen (global) -->
        <RouterLink
          v-if="mobileSlug"
          :to="`/admin/${mobileSlug}/volunteers`"
          class="relative flex-1 flex flex-col items-center justify-center gap-1 text-gray-400 transition-colors active:scale-95"
          :class="isTabActive('volunteers') ? 'text-primary-600' : ''"
          @click="moreOpen = false"
        >
          <span class="absolute top-0 inset-x-2 h-[3px] rounded-b-full bg-primary-600 transition-transform duration-200 origin-center" :class="isTabActive('volunteers') ? 'scale-x-100' : 'scale-x-0'" />
          <UsersIcon class="w-6 h-6" />
          <span class="text-[0.65rem] font-medium leading-none">Helfer</span>
        </RouterLink>
        <RouterLink
          v-else-if="auth.isAdmin"
          to="/admin/instances"
          class="relative flex-1 flex flex-col items-center justify-center gap-1 text-gray-400 transition-colors active:scale-95"
          :class="isTabActive('instances') ? 'text-primary-600' : ''"
          @click="moreOpen = false"
        >
          <span class="absolute top-0 inset-x-2 h-[3px] rounded-b-full bg-primary-600 transition-transform duration-200 origin-center" :class="isTabActive('instances') ? 'scale-x-100' : 'scale-x-0'" />
          <ServerIcon class="w-6 h-6" />
          <span class="text-[0.65rem] font-medium leading-none">Instanzen</span>
        </RouterLink>

        <!-- Tab 3: Anmeldungen (Instanz) oder Organisatoren (global Admin) -->
        <RouterLink
          v-if="mobileSlug"
          :to="`/admin/${mobileSlug}/registrations`"
          class="relative flex-1 flex flex-col items-center justify-center gap-1 text-gray-400 transition-colors active:scale-95"
          :class="isTabActive('registrations') ? 'text-primary-600' : ''"
          @click="moreOpen = false"
        >
          <span class="absolute top-0 inset-x-2 h-[3px] rounded-b-full bg-primary-600 transition-transform duration-200 origin-center" :class="isTabActive('registrations') ? 'scale-x-100' : 'scale-x-0'" />
          <ClipboardDocumentListIcon class="w-6 h-6" />
          <span class="text-[0.65rem] font-medium leading-none">Anmeldungen</span>
        </RouterLink>
        <RouterLink
          v-else-if="auth.isAdmin"
          to="/admin/organizers"
          class="relative flex-1 flex flex-col items-center justify-center gap-1 text-gray-400 transition-colors active:scale-95"
          :class="isTabActive('organizers') ? 'text-primary-600' : ''"
          @click="moreOpen = false"
        >
          <span class="absolute top-0 inset-x-2 h-[3px] rounded-b-full bg-primary-600 transition-transform duration-200 origin-center" :class="isTabActive('organizers') ? 'scale-x-100' : 'scale-x-0'" />
          <UserGroupIcon class="w-6 h-6" />
          <span class="text-[0.65rem] font-medium leading-none">Orgas</span>
        </RouterLink>

        <!-- Tab 4: Mehr -->
        <button
          class="relative flex-1 flex flex-col items-center justify-center gap-1 transition-colors active:scale-95"
          :class="moreOpen ? 'text-primary-600' : 'text-gray-400'"
          @click="moreOpen = !moreOpen"
        >
          <span class="absolute top-0 inset-x-2 h-[3px] rounded-b-full bg-primary-600 transition-transform duration-200 origin-center" :class="moreOpen ? 'scale-x-100' : 'scale-x-0'" />
          <EllipsisHorizontalCircleIcon class="w-6 h-6" />
          <span class="text-[0.65rem] font-medium leading-none">Mehr</span>
        </button>
      </div>
    </nav>

    <!-- ============================= „MEHR" BOTTOM SHEET ============================= -->
    <Teleport to="body">
      <Transition name="sheet">
        <div v-if="moreOpen" class="fixed inset-0 z-50 flex flex-col justify-end md:hidden">
          <!-- Overlay -->
          <div class="absolute inset-0 bg-black/40" @click="moreOpen = false" />

          <!-- Sheet -->
          <div
            class="relative bg-white rounded-t-2xl shadow-2xl max-h-[80vh] flex flex-col"
            style="padding-bottom: env(safe-area-inset-bottom, 0px)"
          >
            <!-- Header -->
            <div class="flex items-center justify-between px-5 pt-4 pb-3 border-b border-gray-100 flex-shrink-0">
              <div class="min-w-0">
                <p class="font-semibold text-gray-900 truncate">{{ auth.user?.first_name || auth.user?.name || 'Administrator' }}</p>
                <p class="text-xs text-gray-400 truncate">{{ auth.user?.email }}</p>
              </div>
              <button class="p-1.5 rounded-full hover:bg-gray-100 text-gray-500 flex-shrink-0 ml-3" @click="moreOpen = false">
                <XMarkIcon class="w-5 h-5" />
              </button>
            </div>

            <!-- Nav-Kacheln -->
            <div class="overflow-y-auto px-4 py-4 space-y-5">

              <!-- Instanz-Bereich -->
              <template v-if="mobileSlug">
                <div>
                  <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Instanz</p>
                  <div class="grid grid-cols-3 gap-2">
                    <MoreTile :to="`/admin/${mobileSlug}/stands`" :icon="BuildingStorefrontIcon" @nav="moreOpen = false">Stände</MoreTile>
                    <MoreTile :to="`/admin/${mobileSlug}/dates`" :icon="CalendarIcon" @nav="moreOpen = false">Termine</MoreTile>
                    <MoreTile :to="`/admin/${mobileSlug}/shifts`" :icon="ClockIcon" @nav="moreOpen = false">Schichten</MoreTile>
                    <MoreTile :to="`/admin/${mobileSlug}/food`" :icon="ShoppingBagIcon" @nav="moreOpen = false">Essen</MoreTile>
                    <MoreTile :to="`/admin/${mobileSlug}/export`" :icon="ArrowDownTrayIcon" @nav="moreOpen = false">Export</MoreTile>
                    <MoreTile :to="`/admin/${mobileSlug}/import`" :icon="ArrowUpTrayIcon" @nav="moreOpen = false">Import</MoreTile>
                    <MoreTile :to="`/admin/${mobileSlug}/settings`" :icon="CogIcon" @nav="moreOpen = false">Einst.</MoreTile>
                    <MoreTile v-if="auth.isInstanceAdmin" :to="`/admin/${mobileSlug}/activity`" :icon="DocumentTextIcon" @nav="moreOpen = false">Protokoll</MoreTile>
                  </div>
                </div>
              </template>

              <!-- Plattform-Bereich (nur Global-Admins) -->
              <div v-if="auth.isAdmin">
                <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Plattform</p>
                <div class="grid grid-cols-3 gap-2">
                  <MoreTile to="/admin/admins" :icon="ShieldCheckIcon" @nav="moreOpen = false">Admins</MoreTile>
                  <MoreTile to="/admin/settings/global" :icon="AdjustmentsHorizontalIcon" @nav="moreOpen = false">Globale Einst.</MoreTile>
                  <MoreTile to="/admin/settings/mail" :icon="EnvelopeIcon" @nav="moreOpen = false">Mail</MoreTile>
                  <MoreTile to="/admin/activity" :icon="DocumentTextIcon" @nav="moreOpen = false">Protokoll</MoreTile>
                  <MoreTile to="/admin/backup" :icon="CloudArrowUpIcon" @nav="moreOpen = false">Backup</MoreTile>
                  <MoreTile to="/admin/update" :icon="ArrowPathIcon" @nav="moreOpen = false">Update</MoreTile>
                </div>
              </div>

              <!-- Konto -->
              <div>
                <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Konto</p>
                <div class="grid grid-cols-3 gap-2">
                  <MoreTile to="/admin/profile/2fa" :icon="LockClosedIcon" @nav="moreOpen = false">2FA</MoreTile>
                  <MoreTile to="/admin/profile/passkeys" :icon="KeyIcon" @nav="moreOpen = false">Passkeys</MoreTile>
                  <button
                    class="flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl bg-gray-50 hover:bg-red-50 text-gray-600 hover:text-red-600 transition-colors active:scale-95 min-h-[4rem]"
                    @click="auth.logout"
                  >
                    <ArrowRightOnRectangleIcon class="w-6 h-6" />
                    <span class="text-xs font-medium leading-tight text-center">Abmelden</span>
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <ConfirmDialog />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useInstanceStore } from '@/stores/instance'
import { adminApi } from '@/api/admin'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import {
  HomeIcon, UsersIcon, BuildingStorefrontIcon, CalendarIcon, ClockIcon,
  ClipboardDocumentListIcon, ShoppingBagIcon, ArrowDownTrayIcon, ArrowUpTrayIcon,
  CogIcon, DocumentTextIcon, ServerIcon, UserGroupIcon, ShieldCheckIcon,
  AdjustmentsHorizontalIcon, EnvelopeIcon, CloudArrowUpIcon, ArrowPathIcon,
  LockClosedIcon, ArrowRightOnRectangleIcon, KeyIcon, XMarkIcon,
  EllipsisHorizontalCircleIcon,
} from '@heroicons/vue/24/outline'

const auth = useAuthStore()
const instanceStore = useInstanceStore()
const router = useRouter()
const route = useRoute()
const instances = ref([])
const selectedSlug = ref('')
const moreOpen = ref(false)

// Aktueller Slug aus Route oder selectedSlug
const mobileSlug = computed(() => route.params.slug || selectedSlug.value || '')

// Instanzinfo für Logo + Seitentitel aus dem Store
const instanceInfo = computed(() => (mobileSlug.value ? instanceStore.current : null))
const instanceInitial = computed(() => {
  const title = instanceInfo.value?.site_title
  return title ? title.charAt(0).toUpperCase() : 'S'
})

// Padding für den Content-Bereich auf Mobile (Header 56px + BottomNav ~88px)
const mobileContentPad = computed(() =>
  'pt-14 pb-[calc(4.25rem+env(safe-area-inset-bottom,0px))] md:pt-0 md:pb-0'
)

// Prüft ob ein Tab aktiv ist (anhand des aktuellen Pfads)
function isTabActive(key) {
  const path = route.path
  switch (key) {
    case 'dashboard': return path.endsWith('/dashboard')
    case 'volunteers': return path.includes('/volunteers')
    case 'registrations': return path.includes('/registrations')
    case 'instances': return path === '/admin/instances' || path.startsWith('/admin/instances/')
    case 'organizers': return path === '/admin/organizers' || path.startsWith('/admin/organizers/')
    default: return false
  }
}

onMounted(async () => {
  if (auth.isStaff) {
    try {
      const res = await adminApi.getInstances({ per_page: 100 })
      instances.value = res.data.data
      if (auth.isOrganizer && instances.value.length === 1) {
        selectedSlug.value = instances.value[0].slug
        router.push(`/admin/${selectedSlug.value}/volunteers`)
      }
    } catch { /* ignore */ }
  }
})

// Route-Slug mit selectedSlug synchronisieren + Theme anwenden
watch(() => route.params.slug, (slug) => {
  if (slug) {
    selectedSlug.value = slug
    instanceStore.loadInstance(slug).catch(() => {})
  } else if (!selectedSlug.value) {
    instanceStore.clear()
  }
}, { immediate: true })

// Theme anwenden/zurücksetzen wenn sich Instanz über den Selector ändert
watch(selectedSlug, (slug) => {
  if (!slug) {
    instanceStore.clear()
  } else {
    instanceStore.loadInstance(slug).catch(() => {})
  }
})

// Mehr-Sheet bei Navigation schließen
watch(() => route.path, () => { moreOpen.value = false })

// Seitentitel aktualisieren wenn Instanz wechselt
watch(instanceInfo, (info) => {
  if (info?.site_title) document.title = info.site_title
})

function onInstanceChange() {
  moreOpen.value = false
  if (selectedSlug.value) {
    router.push(`/admin/${selectedSlug.value}/dashboard`)
  } else {
    router.push('/admin/dashboard')
  }
}
</script>

<!-- NavItem: Desktop-Sidebar-Link -->
<script>
import { defineComponent, h } from 'vue'
import { RouterLink } from 'vue-router'

export const NavItem = defineComponent({
  props: { to: String, icon: Object },
  setup(props, { slots }) {
    return () => h(RouterLink, {
      to: props.to,
      class: 'flex items-center gap-2.5 px-3 py-2 text-sm text-white/60 hover:bg-white/10 hover:text-white rounded-lg transition-colors [&.router-link-active]:bg-white/15 [&.router-link-active]:text-white [&.router-link-active]:font-semibold',
    }, () => [
      props.icon ? h(props.icon, { class: 'w-4 h-4 flex-shrink-0' }) : null,
      slots.default?.(),
    ])
  },
})

// MoreTile: Kachel im „Mehr"-Sheet
export const MoreTile = defineComponent({
  props: { to: String, icon: Object },
  emits: ['nav'],
  setup(props, { slots, emit }) {
    return () => h(RouterLink, {
      to: props.to,
      class: 'flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl bg-gray-50 hover:bg-primary-50 text-gray-600 hover:text-primary-700 transition-colors active:scale-95 min-h-[4rem] [&.router-link-active]:bg-primary-50 [&.router-link-active]:text-primary-700',
      onClick: () => emit('nav'),
    }, () => [
      props.icon ? h(props.icon, { class: 'w-6 h-6' }) : null,
      h('span', { class: 'text-xs font-medium leading-tight text-center' }, slots.default?.()),
    ])
  },
})
</script>

<style scoped>
/* Page transitions */
.page-enter-active { transition: opacity 0.12s ease; }
.page-leave-active { transition: opacity 0.08s ease; }
.page-enter-from, .page-leave-to { opacity: 0; }

/* Bottom-Sheet Slide-up Animation */
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.2s ease;
}
.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}
.sheet-enter-active .relative,
.sheet-leave-active .relative {
  transition: transform 0.25s cubic-bezier(0.32, 0.72, 0, 1);
}
.sheet-enter-from .relative,
.sheet-leave-to .relative {
  transform: translateY(100%);
}
</style>
