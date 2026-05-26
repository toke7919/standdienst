<template>
  <div>
    <h1 class="text-2xl font-bold text-ink mb-6">Mail-Einstellungen</h1>
    <div v-if="loading" class="flex justify-center py-12"><LoadingSpinner size="lg" /></div>

    <div v-else class="space-y-4 max-w-2xl card">
      <div class="flex items-center justify-between">
        <span class="text-sm text-muted">SMTP-Konfiguration</span>
        <button v-if="!editing" type="button" class="btn-secondary text-sm" @click="startEdit">Bearbeiten</button>
      </div>

      <form @submit.prevent="save">
        <div class="space-y-4">
          <div>
            <label class="label">SMTP-Server</label>
            <input v-model="form.mail_server" class="input" :disabled="!editing" />
          </div>
          <div>
            <label class="label">Port</label>
            <input v-model.number="form.mail_port" type="number" class="input max-w-xs" :disabled="!editing" />
          </div>
          <div class="flex items-center gap-2">
            <input v-model="form.mail_use_tls" type="checkbox" id="tls" :disabled="!editing" />
            <label for="tls" class="text-sm text-ink/80">TLS verwenden</label>
          </div>
          <div>
            <label class="label">Benutzername</label>
            <input v-model="form.mail_username" class="input" :disabled="!editing" />
          </div>
          <div>
            <label class="label">Passwort</label>
            <input v-model="form.mail_password" type="password" class="input" :disabled="!editing" />
          </div>
          <div>
            <label class="label">Absender-E-Mail</label>
            <input v-model="form.mail_default_sender" type="email" class="input" :disabled="!editing" />
          </div>
          <div>
            <label class="label">Absender-Name</label>
            <input v-model="form.mail_sender_name" class="input" :disabled="!editing" />
          </div>

          <p v-if="saveError" class="text-sm text-red-600">{{ saveError }}</p>

          <div v-if="editing" class="flex gap-3 flex-wrap">
            <button type="submit" class="btn-primary" :disabled="saving">
              <LoadingSpinner v-if="saving" size="sm" />
              Speichern
            </button>
            <button type="button" class="btn-secondary" @click="cancelEdit">Abbrechen</button>
          </div>
        </div>
      </form>

      <!-- Testmail -->
      <div class="border-t border-sand pt-4 flex flex-wrap items-end gap-3">
        <div>
          <label class="label">Testmail an</label>
          <input v-model="testRecipient" type="email" class="input text-sm" placeholder="empfaenger@beispiel.de" />
        </div>
        <button type="button" class="btn-secondary" :disabled="testing" @click="sendTest">
          <LoadingSpinner v-if="testing" size="sm" />
          Senden
        </button>
      </div>
    </div>

    <!-- Mail-Typ-Test-Center -->
    <div v-if="!loading" class="max-w-2xl mt-6 card space-y-4">
      <h2 class="text-base font-semibold text-ink">Mail-Typen testen</h2>
      <p class="text-xs text-muted">Mails werden mit Beispieldaten befüllt. Instanz-Kontext beeinflusst den Absendernamen und die Links.</p>

      <div>
        <label class="label">Mail-Typen auswählen</label>
        <div class="border border-sand rounded-lg divide-y divide-sand">
          <label
            v-for="mt in MAIL_TYPES"
            :key="mt.value"
            class="flex items-start gap-3 px-3 py-2.5 hover:bg-bg-warm cursor-pointer"
          >
            <input type="checkbox" :value="mt.value" v-model="selectedTypes" class="mt-0.5 rounded" />
            <div class="min-w-0">
              <span class="text-sm font-medium text-ink">{{ mt.label }}</span>
              <span class="text-xs text-muted block">{{ mt.desc }}</span>
            </div>
          </label>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label">Instanz <span class="text-muted font-normal text-xs">(optional)</span></label>
          <select v-model="typedTestSlug" class="input">
            <option value="">Plattform (kein Instanz-Kontext)</option>
            <option v-for="inst in instances" :key="inst.id" :value="inst.slug">{{ inst.name }}</option>
          </select>
        </div>
        <div>
          <label class="label">Empfänger-E-Mail</label>
          <input v-model="typedTestRecipient" type="email" class="input" placeholder="test@beispiel.de" />
        </div>
      </div>

      <button
        type="button"
        class="btn-primary"
        :disabled="typedTesting || !selectedTypes.length || !typedTestRecipient"
        @click="sendTypedTests"
      >
        <LoadingSpinner v-if="typedTesting" size="sm" />
        {{ selectedTypes.length ? `${selectedTypes.length} Testmail(s) senden` : 'Typ auswählen' }}
      </button>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/api/admin'
import { useUiStore } from '@/stores/ui'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const MAIL_TYPES = [
  { value: 'welcome',           label: 'Willkommens-Mail',         desc: 'Wird an Volunteers gesendet, die sich ohne Passwort registriert haben' },
  { value: 'organizer_invite',  label: 'Organisator-Einladung',    desc: 'Wird beim Anlegen eines neuen Organisators versendet' },
  { value: 'reset',             label: 'Passwort-Reset',           desc: 'Wird bei einer Passwort-Zurücksetzen-Anfrage versendet' },
  { value: 'shift_confirmation',label: 'Schicht-Bestätigung',      desc: 'Wird nach erfolgreicher Schicht-Anmeldung eines Volunteers versendet' },
  { value: 'reminder',          label: 'Erinnerungsmail',          desc: 'Wird täglich um 08:00 Uhr an Volunteers mit aktivierten Benachrichtigungen gesendet' },
  { value: 'digest',            label: 'Organisator-Tages-Digest', desc: 'Wird täglich um 18:00 Uhr an Organisatoren gesendet' },
  { value: 'dsgvo_auskunft',    label: 'DSGVO-Datenauskunft',      desc: 'Wird auf Anfrage des Volunteers versendet (Art. 15 DSGVO)' },
]

const ui = useUiStore()
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const editing = ref(false)
const saveError = ref('')
const testRecipient = ref('')
const form = ref({})
const savedForm = ref({})
const instances = ref([])

const selectedTypes = ref([])
const typedTestSlug = ref('')
const typedTestRecipient = ref('')
const typedTesting = ref(false)

onMounted(async () => {
  try {
    const [mailRes, instRes] = await Promise.all([
      adminApi.getMailSettings(),
      adminApi.getInstances({ per_page: 200 }),
    ])
    form.value = mailRes.data.data
    savedForm.value = { ...mailRes.data.data }
    instances.value = instRes.data.data
  } finally {
    loading.value = false
  }
})

function startEdit() {
  savedForm.value = { ...form.value }
  editing.value = true
  saveError.value = ''
}

function cancelEdit() {
  form.value = { ...savedForm.value }
  editing.value = false
  saveError.value = ''
}

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    const res = await adminApi.updateMailSettings(form.value)
    form.value.updated_at = res.data.data.updated_at
    savedForm.value = { ...form.value }
    editing.value = false
    ui.success('Gespeichert')
  } catch (e) {
    saveError.value = e.response?.data?.error || 'Fehler'
  } finally {
    saving.value = false
  }
}

async function sendTest() {
  testing.value = true
  try {
    const res = await adminApi.sendTestMail({ to: testRecipient.value || undefined })
    ui.success(res.data.message || 'Testmail gesendet')
  } catch (e) {
    ui.err(e.response?.data?.error || 'Versand fehlgeschlagen')
  } finally {
    testing.value = false
  }
}

async function sendTypedTests() {
  typedTesting.value = true
  for (const type of selectedTypes.value) {
    const label = MAIL_TYPES.find(m => m.value === type)?.label || type
    try {
      await adminApi.sendTypedTestMail({
        type,
        to: typedTestRecipient.value,
        instance_slug: typedTestSlug.value || undefined,
      })
      ui.success(`${label} gesendet`)
    } catch (e) {
      ui.err(`${label}: ${e.response?.data?.error || 'Versand fehlgeschlagen'}`)
    }
  }
  typedTesting.value = false
}
</script>
