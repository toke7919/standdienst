<template>
  <div class="min-h-screen flex flex-col" :style="brandStyle">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 shadow-sm">
      <div class="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
        <RouterLink :to="`/${slug}/shifts`" class="flex items-center gap-2">
          <img
            v-if="settings?.logo_filename"
            :src="`/uploads/${settings.logo_filename}`"
            class="h-8 object-contain"
            alt="Logo"
          />
          <span class="font-semibold text-gray-900">{{ settings?.site_title || 'Standdienst' }}</span>
        </RouterLink>
        <nav class="flex items-center gap-1">
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

    <main class="flex-1 max-w-4xl mx-auto w-full px-4 py-6">
      <RouterView />
    </main>

    <footer class="border-t border-gray-200 bg-white mt-auto">
      <div class="max-w-4xl mx-auto px-4 py-3 flex gap-4 text-xs text-gray-400">
        <RouterLink :to="`/${slug}/impressum`" class="hover:text-gray-600">Impressum</RouterLink>
        <RouterLink :to="`/${slug}/privacy`" class="hover:text-gray-600">Datenschutz</RouterLink>
      </div>
    </footer>

    <ConfirmDialog />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useInstanceStore } from '@/stores/instance'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const auth = useAuthStore()
const instanceStore = useInstanceStore()
const route = useRoute()

const slug = computed(() => route.params.slug)
const settings = computed(() => instanceStore.current?.settings)

const brandStyle = computed(() => {
  const color = settings.value?.primary_color
  return color ? { '--color-primary': color } : {}
})

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

onMounted(() => {
  if (slug.value && !instanceStore.current) {
    instanceStore.loadInstance(slug.value)
  }
})
</script>
