<template>
  <footer class="border-t border-sand bg-soft mt-auto">
    <div class="max-w-4xl mx-auto px-4 py-3 flex items-center gap-4">
      <div class="flex gap-4 text-xs text-muted">
        <RouterLink
          :to="slug ? `/${slug}/impressum` : '/impressum'"
          class="hover:text-ink/80 transition-colors"
        >Impressum</RouterLink>
        <RouterLink
          v-if="slug"
          :to="`/${slug}/datenschutz`"
          class="hover:text-ink/80 transition-colors"
        >Datenschutz</RouterLink>
      </div>
      <span v-if="copyright" class="text-xs text-muted truncate ml-auto">{{ copyright }}</span>
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
