<template>
  <div class="min-h-screen bg-gray-50 flex">
    <!-- Sidebar -->
    <aside class="w-64 bg-white border-r border-gray-200 flex flex-col fixed inset-y-0">
      <div class="p-5 border-b border-gray-100">
        <RouterLink to="/admin/dashboard" class="flex items-center gap-2">
          <div class="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <span class="text-white text-sm font-bold">S</span>
          </div>
          <span class="font-semibold text-gray-900">Standdienst</span>
        </RouterLink>
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
        <NavItem to="/admin/dashboard" :icon="HomeIcon">Dashboard</NavItem>

        <template v-if="selectedSlug">
          <p class="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wide mt-3">
            Instanz
          </p>
          <NavItem :to="`/admin/${selectedSlug}/volunteers`" :icon="UsersIcon">Helfer</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/stands`" :icon="BuildingStorefrontIcon">Stände</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/dates`" :icon="CalendarIcon">Termine</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/shifts`" :icon="ClockIcon">Schichten</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/registrations`" :icon="ClipboardDocumentListIcon">Anmeldungen</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/food`" :icon="ShoppingBagIcon">Essensspenden</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/export`" :icon="ArrowDownTrayIcon">Export</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/import`" :icon="ArrowUpTrayIcon">Import</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/settings`" :icon="CogIcon">Einstellungen</NavItem>
          <NavItem :to="`/admin/${selectedSlug}/activity`" :icon="DocumentTextIcon">Protokoll</NavItem>
        </template>

        <template v-if="auth.isAdmin">
          <p class="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wide mt-3">
            Plattform
          </p>
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

      <div class="p-3 border-t border-gray-100">
        <NavItem to="/admin/profile/2fa" :icon="LockClosedIcon">2FA einrichten</NavItem>
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
    <main class="flex-1 ml-64 p-6 min-h-screen">
      <RouterView />
    </main>

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
  LockClosedIcon, ArrowRightOnRectangleIcon,
} from '@heroicons/vue/24/outline'

const auth = useAuthStore()
const router = useRouter()
const instances = ref([])
const selectedSlug = ref('')

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
  if (selectedSlug.value) {
    router.push(`/admin/${selectedSlug.value}/volunteers`)
  } else {
    router.push('/admin/dashboard')
  }
}
</script>

<script>
// NavItem helper component defined inline to avoid an extra file
import { defineComponent, h } from 'vue'
import { RouterLink } from 'vue-router'

export const NavItem = defineComponent({
  props: { to: String, icon: Object },
  setup(props, { slots }) {
    return () => h(RouterLink, {
      to: props.to,
      class: 'flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors [&.router-link-active]:bg-primary-50 [&.router-link-active]:text-primary-700 [&.router-link-active]:font-medium',
    }, () => [
      props.icon ? h(props.icon, { class: 'w-4 h-4 flex-shrink-0' }) : null,
      slots.default?.(),
    ])
  },
})
</script>
