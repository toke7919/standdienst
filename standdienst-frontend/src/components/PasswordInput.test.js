import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/vue'
import { ref } from 'vue'
import PasswordInput from './PasswordInput.vue'

// Regression: Im sichtbaren Modus (Auge-Symbol) ist das Feld ein Textfeld.
// Mobile Tastaturen haben dort Großschreibung/Autokorrektur/Wortvorschläge
// angewandt – gespeichert wurde ein anderes Passwort als gedacht, der Login
// schlug danach mit „Ungültige Anmeldedaten“ fehl.

function field(container) {
  return container.querySelector('input')
}

describe('PasswordInput', () => {
  it('ist zunächst verdeckt und lässt sich sichtbar und wieder verdeckt schalten', async () => {
    const { container } = render(PasswordInput, { props: { modelValue: '' } })
    expect(field(container).type).toBe('password')

    await fireEvent.click(screen.getByRole('button', { name: 'Passwort anzeigen' }))
    expect(field(container).type).toBe('text')

    await fireEvent.click(screen.getByRole('button', { name: 'Passwort verbergen' }))
    expect(field(container).type).toBe('password')
  })

  it('schaltet Autokorrektur, Großschreibung und Rechtschreibprüfung ab – auch im sichtbaren Modus', async () => {
    const { container } = render(PasswordInput, { props: { modelValue: '' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Passwort anzeigen' }))
    const input = field(container)
    expect(input.getAttribute('autocapitalize')).toBe('off')
    expect(input.getAttribute('autocorrect')).toBe('off')
    expect(input.getAttribute('spellcheck')).toBe('false')
  })

  it('reicht autocomplete, placeholder und required ans Feld durch', () => {
    const { container } = render(PasswordInput, {
      props: { modelValue: '' },
      attrs: { autocomplete: 'current-password', placeholder: 'Mindestens 8 Zeichen', required: true },
    })
    const input = field(container)
    expect(input.getAttribute('autocomplete')).toBe('current-password')
    expect(input.getAttribute('placeholder')).toBe('Mindestens 8 Zeichen')
    expect(input.required).toBe(true)
  })

  it('autocomplete ist standardmäßig new-password', () => {
    const { container } = render(PasswordInput, { props: { modelValue: '' } })
    expect(field(container).getAttribute('autocomplete')).toBe('new-password')
  })

  it('gibt die Eingabe unverändert per v-model weiter', async () => {
    const value = ref('')
    const { container } = render({
      components: { PasswordInput },
      setup: () => ({ value }),
      template: '<PasswordInput v-model="value" />',
    })
    await fireEvent.update(field(container), 'sommer2026 Ü!')
    expect(value.value).toBe('sommer2026 Ü!')
  })
})
