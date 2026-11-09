import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/vue'

const { api, authState } = vi.hoisted(() => ({
  api: {
    getVolunteers: vi.fn(),
    createVolunteer: vi.fn(),
    updateVolunteer: vi.fn(),
    deleteVolunteer: vi.fn(),
  },
  authState: { isAdmin: false, isInstanceAdminFor: vi.fn() },
}))

vi.mock('@/api/admin', () => ({ adminApi: api }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => authState }))
vi.mock('@/stores/ui', () => ({ useUiStore: () => ({ success: vi.fn(), err: vi.fn(), confirm: vi.fn() }) }))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { slug: 'test' } }),
  RouterLink: { template: '<a><slot /></a>' },
}))

import Volunteers from './Volunteers.vue'

beforeEach(() => {
  vi.clearAllMocks()
  api.getVolunteers.mockResolvedValue({
    data: { data: [{ id: 1, name: 'Max Muster', display_name: 'Max Muster', email: 'max@test.de' }], pages: 1, total: 1 },
  })
})

describe('Helfer-Liste', () => {
  it('Organisator kann anlegen und bearbeiten, aber nicht löschen', async () => {
    authState.isInstanceAdminFor.mockReturnValue(false)
    render(Volunteers)
    expect((await screen.findAllByText('Bearbeiten')).length).toBeGreaterThan(0)
    expect(screen.getByText('Neuer Helfer')).toBeInTheDocument()
    expect(screen.queryByText('Löschen')).not.toBeInTheDocument()
  })

  it('Instanz-Admin sieht „Löschen“', async () => {
    authState.isInstanceAdminFor.mockReturnValue(true)
    render(Volunteers)
    expect((await screen.findAllByText('Löschen')).length).toBeGreaterThan(0)
  })

  it('Organisator sieht beim Anlegen kein Passwort-Feld, aber den Willkommens-Hinweis', async () => {
    authState.isInstanceAdminFor.mockReturnValue(false)
    render(Volunteers)
    await fireEvent.click(await screen.findByRole('button', { name: 'Neuer Helfer' }))
    expect(screen.queryByText('Passwort')).not.toBeInTheDocument()
    const email = document.querySelector('input[type="email"]')
    await fireEvent.update(email, 'neu@test.de')
    expect(screen.getByText(/Willkommens-E-Mail zum Einrichten/)).toBeInTheDocument()
  })

  it('Instanz-Admin sieht beim Anlegen das Passwort-Feld', async () => {
    authState.isInstanceAdminFor.mockReturnValue(true)
    render(Volunteers)
    await fireEvent.click(await screen.findByRole('button', { name: 'Neuer Helfer' }))
    expect(screen.getByText('Passwort')).toBeInTheDocument()
  })
})
