<template>
  <div class="min-h-screen bg-gray-50 flex">
    <!-- Overlay für Mobile -->
    <div
      v-if="drawerOpen"
      class="fixed inset-0 bg-black/40 z-30 md:hidden"
      @click="drawerOpen = false"
    />

    <!-- Sidebar (Desktop: immer sichtbar, Mobile: Drawer) -->
    <aside
      :class="[
        'bg-white border-r border-gray-200 flex flex-col fixed inset-y-0 z-40 transition-transform duration-200',
        'w-64',
        drawerOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
      ]"
    >
      <div class="p-5 border-b border-gray-100 flex items-center justify-between">
        <RouterLink to="/admin/dashboard" class="flex items-center gap-2">
          <div class="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <span class="text-white text-sm font-bold">S</span>
          </div>
          <span class="font-semibold text-gray-900">Standdienst</span>
        </RouterLink>
        <button class="md:hidden p-1 text-gray-400 hover:text-gray-600" @click="drawerOpen = false">
          <XMarkIcon class="w-5 h-5" />
        </button>
      </div>

      <!-- Instance selector -->
      <div v-if="auth.isLoggedIn" class="p-3 border-b border-gray-100">
        <select
          v-model="selectedSlug"
          class="input text-sm"
          @change="onInstanceChange"
        >
          <option value="">Alle Instanzen</option>
          <option v-for="inst in instances" :key="inst.id" :value="inst.slug">
            {{ inst.name }}
          </option>
        </select>
      </div>

      <nav class="flex-1 overflow-y-auto p-3 space-y-1">
        <NavItem :to="selectedSlug ? `/admin/${selectedSlug}/dashboard` : '/admin/dashboard'" :icon="HomeIcon" @click="drawerOpen = false">Dashboard</NavItem>

        <template v-if="selectedSlug">
          <p class="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wide mt-3">
            Instanz
          </p>
          <NavItem :to="`/admin/${selectedSlug}/volunteers`" :icon="UsersIcon" @click="drawerOpen = false">Helfer</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/stands`" :icon="BuildingStorefrontIcon" @click="drawerOpen = false">Stände</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/dates`" :icon="CalendarIcon" @click="drawerOpen = false">Termine</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/shifts`" :icon="ClockIcon" @click="drawerOpen = false">Schichten</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/registrations`" :icon="ClipboardDocumentListIcon" @click="drawerOpen = false">Anmeldungen</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/food`" :icon="ShoppingBagIcon" @click="drawerOpen = false">Essensspenden</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/export`" :icon="ArrowDownTrayIcon" @click="drawerOpen = false">Export</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/import`" :icon="ArrowUpTrayIcon" @click="drawerOpen = false">Import</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/settings`" :icon="CogIcon" @click="drawerOpen = false">Einstellungen</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/activity`" :icon="DocumentTextIcon" @click="drawerOpen = false">Protokoll</NavItem>
        </template>

        <template v-if="auth.isAdmin">
          <p class="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wide mt-3">
            Plattform
          </p>
          <NavItem to="/admin/instances" :icon="ServerIcon" @click="drawerOpen = false">Instanzen</NavItem>
          <NavItem to="/admin/organizers" :icon="UserGroupIcon" @click="drawerOpen = false">Organisatoren</NavItem>
          <NavItem to="/admin/admins" :icon="ShieldCheckIcon" @click="drawerOpen = false">Admins</NavItem>
          <NavItem to="/admin/settings/global" :icon="AdjustmentsHorizontalIcon" @click="drawerOpen = false">Globale Einst.</NavItem>
          <NavItem to="/admin/settings/mail" :icon="EnvelopeIcon" @click="drawerOpen = false">Mail-Einst.</NavItem>
          <NavItem to="/admin/activity" :icon="DocumentTextIcon" @click="drawerOpen = false">Globales Protokoll</NavItem>
          <NavItem to="/admin/backup" :icon="CloudArrowUpIcon" @click="drawerOpen = false">Backup</NavItem>
          <NavItem to="/admin/update" :icon="ArrowPathIcon" @click="drawerOpen = false">Update</NavItem>
        </template>
      </nav>

      <div class="p-3 border-t border-gray-100">
        <NavItem to="/admin/profile/2fa" :icon="LockClosedIcon" @click="drawerOpen = false">2FA einrichten</NavItem>
        <NavItem to="/admin/profile/passkeys" :icon="KeyIcon" @click="drawerOpen = false">Passkeys</NavItem>
        <button
          class="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          @click="auth.logout"
        >
          <ArrowRightOnRectangleIcon class="w-4 h-4" />
          Abmelden
        </button>
      </div>
    </aside>

    <!-- Main content -->
    <div class="flex-1 md:ml-64 flex flex-col min-h-screen">
      <!-- Mobile Header -->
      <header class="md:hidden sticky top-0 z-20 bg-white border-b border-gray-200 flex items-center gap-3 px-4 py-3 shadow-sm">
        <button class="p-1 text-gray-600 hover:text-gray-900" @click="drawerOpen = true">
          <Bars3Icon class="w-6 h-6" />
        </button>
        <span class="font-semibold text-gray-900 text-sm">Standdienst Admin</span>
        <div class="ml-auto">
          <select
            v-if="auth.isLoggedIn"
            v-model="selectedSlug"
            class="text-xs border border-gray-200 rounded-lg px-2 py-1 bg-white"
            @change="onInstanceChange"
          >
            <option value="">Alle</option>
            <option v-for="inst in instances" :key="inst.id" :value="inst.slug">
              {{ inst.name }}
            </option>
          </select>
        </div>
      </header>

      <main class="flex-1 p-4 md:p-6">
        <RouterView />
      </main>
    </div>

    <ConfirmDialog />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { adminApi } from '@/api/admin'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import {
  HomeIcon, UsersIcon, BuildingStorefrontIcon, CalendarIcon, ClockIcon,
  ClipboardDocumentListIcon, ShoppingBagIcon, ArrowDownTrayIcon, ArrowUpTrayIcon,
  CogIcon, DocumentTextIcon, ServerIcon, UserGroupIcon, ShieldCheckIcon,
  AdjustmentsHorizontalIcon, EnvelopeIcon, CloudArrowUpIcon, ArrowPathIcon,
  LockClosedIcon, ArrowRightOnRectangleIcon, KeyIcon, XMarkIcon, Bars3Icon,
} from '@heroicons/vue/24/outline'

const auth = useAuthStore()
const router = useRouter()
const instances = ref([])
const selectedSlug = ref('')
const drawerOpen = ref(false)

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

function onInstanceChange() {
  drawerOpen.value = false
  if (selectedSlug.value) {
    router.push(`/admin/${selectedSlug.value}/volunteers`)
  } else {
    router.push('/admin/dashboard')
  }
}
</script>

<script>
import { defineComponent, h } from 'vue'
import { RouterLink } from 'vue-router'

export const NavItem = defineComponent({
  props: { to: String, icon: Object },
  emits: ['click'],
  setup(props, { slots, emit }) {
    return () => h(RouterLink, {
      to: props.to,
      class: 'flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors [&.router-link-active]:bg-primary-50 [&.router-link-active]:text-primary-700 [&.router-link-active]:font-medium',
      onClick: () => emit('click'),
    }, () => [
      props.icon ? h(props.icon, { class: 'w-4 h-4 flex-shrink-0' }) : null,
      slots.default?.(),
    ])
  },
})
</script>
