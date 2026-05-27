<template>
  <div class="min-h-screen bg-bg-brand flex flex-col items-center justify-center px-4">
    <div class="text-center max-w-md">
      <img src="/assets/mark-ticket.svg" alt="Standdienst" class="h-16 mx-auto mb-4 drop-shadow" />
      <img src="/assets/wordmark.svg" alt="Standdienst" class="h-6 mx-auto mb-10 opacity-80" />

      <div class="w-12 h-12 rounded-2xl bg-amber-100 flex items-center justify-center mx-auto mb-5">
        <WrenchScrewdriverIcon class="w-6 h-6 text-amber-600" />
      </div>
      <h1 class="text-2xl font-bold text-ink mb-3">Wartungsarbeiten</h1>
      <p class="text-muted text-base leading-relaxed">
        Das System wird gerade aktualisiert oder gewartet.<br>
        Bitte versuche es in wenigen Minuten erneut.
      </p>
    </div>
  </div>
</template>

<script setup>
import { WrenchScrewdriverIcon } from '@heroicons/vue/24/outline'
</script>
