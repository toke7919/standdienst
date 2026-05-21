<template>
  <footer class="border-t border-gray-200 bg-white mt-auto">
    <div class="max-w-4xl mx-auto px-4 py-3 flex items-center gap-4">
      <div class="flex gap-4 text-xs text-gray-400">
        <RouterLink
          :to="slug ? `/${slug}/impressum` : '/impressum'"
          class="hover:text-gray-600 transition-colors"
        >Impressum</RouterLink>
        <RouterLink
          v-if="slug"
          :to="`/${slug}/datenschutz`"
          class="hover:text-gray-600 transition-colors"
        >Datenschutz</RouterLink>
      </div>
      <span v-if="copyright" class="text-xs text-gray-400 truncate ml-auto">{{ copyright }}</span>
    </div>
  </footer>
</template>

<script setup>
import { RouterLink } from 'vue-router'

defineProps({
  slug: { type: String, default: '' },
  copyright: { type: String, default: '' },
})
</script>
