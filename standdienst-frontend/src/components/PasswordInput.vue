<template>
  <div class="relative">
    <!-- Sichtbarer Modus = Textfeld: ohne autocapitalize/autocorrect/spellcheck
         verändern mobile Tastaturen das Passwort unbemerkt. -->
    <input
      v-bind="$attrs"
      :value="modelValue"
      :type="show ? 'text' : 'password'"
      class="input pr-10"
      :autocomplete="autocomplete"
      autocapitalize="off"
      autocorrect="off"
      spellcheck="false"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <button
      type="button"
      class="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink/80"
      :aria-label="show ? 'Passwort verbergen' : 'Passwort anzeigen'"
      @click="show = !show"
    >
      <EyeSlashIcon v-if="show" class="w-4 h-4" />
      <EyeIcon v-else class="w-4 h-4" />
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { EyeIcon, EyeSlashIcon } from '@heroicons/vue/24/outline'

defineOptions({ inheritAttrs: false })
defineProps({
  modelValue: { type: String, default: '' },
  autocomplete: { type: String, default: 'new-password' },
})
defineEmits(['update:modelValue'])

const show = ref(false)
</script>
