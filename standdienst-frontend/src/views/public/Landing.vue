<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 flex flex-col">

    <!-- ===== HERO ===== -->
    <div class="flex-1 flex flex-col items-center justify-center px-6 pt-20 pb-16 text-center">
      <!-- Icon -->
      <div class="w-20 h-20 bg-white/10 rounded-3xl flex items-center justify-center mb-8 border border-white/20 shadow-xl">
        <CalendarDaysIcon class="w-10 h-10 text-white" />
      </div>

      <h1 class="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">Standdienst</h1>
      <p class="text-primary-200 text-lg md:text-xl max-w-2xl leading-relaxed mb-10">
        Die Plattform für Freiwilligenkoordination bei Vereinen und Veranstaltungen.
        Schichten planen, Helfer einteilen und Essensspenden verwalten – einfach, digital und DSGVO-konform.
      </p>

      <div class="flex flex-wrap items-center justify-center gap-3">
        <RouterLink to="/impressum" class="inline-flex items-center gap-2 px-6 py-3 bg-white text-primary-800 font-semibold rounded-xl shadow-lg hover:bg-primary-50 transition-colors duration-150">
          <EnvelopeIcon class="w-4 h-4" />
          Kontakt aufnehmen
        </RouterLink>
        <RouterLink to="/admin/login" class="inline-flex items-center gap-2 px-6 py-3 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-colors duration-150">
          Zum Admin-Bereich
          <ArrowRightIcon class="w-4 h-4" />
        </RouterLink>
      </div>
    </div>

    <!-- ===== FEATURES ===== -->
    <div class="bg-white/5 backdrop-blur-sm border-t border-white/10">
      <div class="max-w-5xl mx-auto px-6 py-16">
        <h2 class="text-center text-white/70 text-sm font-semibold uppercase tracking-widest mb-10">Was Standdienst bietet</h2>

        <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <FeatureCard
            :icon="CalendarDaysIcon"
            title="Schichtplanung"
            text="Termine und Schichten anlegen, Stände organisieren und die Belegung in Echtzeit verfolgen."
          />
          <FeatureCard
            :icon="UsersIcon"
            title="Helfer-Self-Service"
            text="Freiwillige tragen sich selbst ein und aus, verwalten ihr Profil und exportieren Schichten als Kalender."
          />
          <FeatureCard
            :icon="ShoppingBagIcon"
            title="Essensspenden"
            text="Kuchenlisten und Essensspenden koordinieren – mit Kühlungskennzeichnung und Abgabezeiten."
          />
          <FeatureCard
            :icon="ShieldCheckIcon"
            title="DSGVO-konform"
            text="Soft-Delete, Datenauskunft-Export (Art. 15/20) und einwilligungsbasierte Registrierung inklusive."
          />
          <FeatureCard
            :icon="ChartBarIcon"
            title="Dashboard & Export"
            text="Belegungsübersicht, Aktivitätslog sowie Export als CSV, Excel, ODS und iCal."
          />
          <FeatureCard
            :icon="ServerStackIcon"
            title="Multi-Instanz"
            text="Eine Plattform für beliebig viele Vereine oder Veranstaltungen – jede Instanz mit eigenem Branding."
          />
        </div>
      </div>
    </div>

    <!-- ===== KONTAKT ===== -->
    <div class="max-w-2xl mx-auto px-6 py-16 text-center">
      <h2 class="text-2xl font-bold text-white mb-4">Interesse geweckt?</h2>
      <p class="text-primary-200 mb-8 leading-relaxed">
        Du leitest einen Verein oder planst eine Veranstaltung und möchtest Standdienst einsetzen?
        Nimm Kontakt mit uns auf – wir richten gerne eine Instanz für deine Organisation ein.
      </p>
      <RouterLink
        to="/impressum"
        class="inline-flex items-center gap-2 px-8 py-3.5 bg-white text-primary-800 font-semibold rounded-xl shadow-lg hover:bg-primary-50 transition-colors duration-150"
      >
        <EnvelopeIcon class="w-5 h-5" />
        Kontaktdaten im Impressum
      </RouterLink>
    </div>

    <!-- ===== FOOTER ===== -->
    <div class="border-t border-white/10 px-6 py-5">
      <div class="max-w-5xl mx-auto flex flex-wrap items-center justify-between gap-3">
        <p class="text-primary-400 text-sm">{{ copyrightText }}</p>
        <div class="flex gap-5 text-sm text-primary-400">
          <RouterLink to="/admin/login" class="hover:text-white transition-colors">Admin-Bereich</RouterLink>
          <RouterLink to="/impressum" class="hover:text-white transition-colors">Impressum</RouterLink>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, defineComponent, h } from 'vue'
import { RouterLink } from 'vue-router'
import {
  CalendarDaysIcon, UsersIcon, ShoppingBagIcon,
  ShieldCheckIcon, ChartBarIcon, ServerStackIcon,
  EnvelopeIcon, ArrowRightIcon,
} from '@heroicons/vue/24/outline'
import { publicApi } from '@/api/public'

const copyrightText = ref('Standdienst')

onMounted(async () => {
  try {
    // Copyright-Text aus irgendeiner aktiven Instanz holen, falls vorhanden
    const res = await publicApi.getInstances()
    if (res.data.data?.length) {
      const info = await publicApi.getInstanceInfo(res.data.data[0].slug)
      if (info.data.data?.copyright_text) {
        copyrightText.value = info.data.data.copyright_text
      }
    }
  } catch { /* ignorieren */ }
})

const FeatureCard = defineComponent({
  props: { icon: Object, title: String, text: String },
  setup(props) {
    return () => h('div', {
      class: 'bg-white/10 border border-white/10 rounded-2xl p-5 flex flex-col gap-3',
    }, [
      h('div', { class: 'w-10 h-10 bg-primary-700/60 rounded-xl flex items-center justify-center flex-shrink-0' }, [
        props.icon ? h(props.icon, { class: 'w-5 h-5 text-primary-200' }) : null,
      ]),
      h('div', {}, [
        h('p', { class: 'font-semibold text-white text-sm mb-1' }, props.title),
        h('p', { class: 'text-primary-300 text-sm leading-relaxed' }, props.text),
      ]),
    ])
  },
})
</script>
