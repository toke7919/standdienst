<template>
  <div class="min-h-screen flex flex-col items-center justify-center text-center p-4">
    <p class="text-8xl font-bold text-sand">404</p>
    <h1 class="text-2xl font-semibold text-ink/80 mt-4">Seite nicht gefunden</h1>
    <p class="text-muted mt-2">Diese Seite existiert nicht.</p>
    <RouterLink to="/" class="mt-6 btn-primary">Zur Startseite</RouterLink>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>
