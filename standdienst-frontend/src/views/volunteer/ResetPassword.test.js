import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/vue'

const { api } = vi.hoisted(() => ({ api: { resetPassword: vi.fn() } }))

vi.mock('@/api/public', () => ({ publicApi: api }))
vi.mock('@/stores/instance', () => ({
  useInstanceStore: () => ({ current: { site_title: 'Reitverein' }, loadInstance: vi.fn() }),
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { slug: 'reitverein' }, query: { token: 'tok123' } }),
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
}))

import ResetPassword from './ResetPassword.vue'

function passwordField(container) {
  return container.querySelector('input')
}

beforeEach(() => vi.clearAllMocks())

describe('Helfer: Neues Passwort setzen', () => {
  it('Passwortfeld ist auch sichtbar geschaltet vor Autokorrektur geschützt', async () => {
    const { container } = render(ResetPassword)
    await fireEvent.click(screen.getByRole('button', { name: 'Passwort anzeigen' }))
    const input = passwordField(container)
    expect(input.type).toBe('text')
    expect(input.getAttribute('autocapitalize')).toBe('off')
    expect(input.getAttribute('autocorrect')).toBe('off')
    expect(input.getAttribute('spellcheck')).toBe('false')
  })

  it('sendet Token und Passwort unverändert und zeigt danach den Erfolg', async () => {
    api.resetPassword.mockResolvedValue({ data: {} })
    const { container } = render(ResetPassword)
    await fireEvent.update(passwordField(container), 'sommer2026')
    await fireEvent.click(screen.getByRole('button', { name: /Passwort setzen/ }))
    expect(api.resetPassword).toHaveBeenCalledWith('reitverein', 'tok123', 'sommer2026')
    expect(await screen.findByText(/Passwort geändert/)).toBeInTheDocument()
  })

  it('zeigt die Fehlermeldung des Servers', async () => {
    api.resetPassword.mockRejectedValue({ response: { data: { error: 'Ungültiger oder abgelaufener Reset-Link' } } })
    const { container } = render(ResetPassword)
    await fireEvent.update(passwordField(container), 'sommer2026')
    await fireEvent.click(screen.getByRole('button', { name: /Passwort setzen/ }))
    expect(await screen.findByText('Ungültiger oder abgelaufener Reset-Link')).toBeInTheDocument()
  })
})
