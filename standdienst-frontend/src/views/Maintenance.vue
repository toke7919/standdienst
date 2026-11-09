<template>
  <div class="min-h-screen bg-bg-brand flex flex-col items-center justify-center px-4">
    <div class="text-center max-w-md">
      <img src="/assets/mark-ticket.svg" alt="Standdienst" class="h-16 mx-auto mb-4 drop-shadow-sm" />
      <img src="/assets/wordmark.svg" alt="Standdienst" class="h-6 mx-auto mb-10 opacity-80" />

      <div class="w-12 h-12 rounded-2xl bg-amber-100 flex items-center justify-center mx-auto mb-5">
        <WrenchScrewdriverIcon class="w-6 h-6 text-amber-600" />
      </div>
      <h1 class="text-2xl font-bold text-ink mb-3">Wartungsarbeiten</h1>
      <p class="text-muted text-base leading-relaxed">
        Die Seite befindet sich gerade im Wartungsmodus<br>
        und ist in wenigen Augenblicken wieder verfügbar.
      </p>
      <p class="flex items-center justify-center gap-2 text-sm text-muted mt-6">
        <LoadingSpinner size="sm" />
        Die Seite lädt automatisch neu, sobald alles bereit ist.
      </p>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { WrenchScrewdriverIcon } from '@heroicons/vue/24/outline'
import { setupApi } from '@/api/setup'
import { useSetupStore } from '@/stores/setup'
import { useAuthStore } from '@/stores/auth'
import { mayBypassMaintenance } from '@/utils/maintenance'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const POLL_MS = 5000

const route = useRoute()
const setup = useSetupStore()
const auth = useAuthStore()

let _interval = null

// Nur interne Pfade als Rücksprungziel (kein Open Redirect über ?redirect=//…)
function target() {
  const r = route.query.redirect
  return typeof r === 'string' && r.startsWith('/') && !r.startsWith('//') ? r : '/'
}

async function poll() {
  let mode
  try {
    const res = await setupApi.status()
    mode = res.data.data.maintenance_mode ?? false
  } catch {
    return // API noch nicht erreichbar (Neustart läuft) – beim nächsten Intervall erneut prüfen
  }
  setup.setMaintenance(mode)
  // Vollständig neu laden statt Router-Navigation: nach einem Update liegt ein neuer Frontend-Build vor
  if (!mode || mayBypassMaintenance(target(), auth.isAdmin)) {
    clearInterval(_interval)
    window.location.replace(target())
  }
}

onMounted(() => {
  _interval = setInterval(poll, POLL_MS)
})

onUnmounted(() => {
  clearInterval(_interval)
})
</script>
