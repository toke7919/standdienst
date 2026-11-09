import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/vue'

const { api, authState } = vi.hoisted(() => ({
  api: {
    getSiteSettings: vi.fn(),
    updateSiteSettings: vi.fn(),
    clearInstanceData: vi.fn(),
    deleteLogo: vi.fn(),
    uploadLogo: vi.fn(),
  },
  authState: { isAdmin: false, isInstanceAdminFor: vi.fn() },
}))

vi.mock('@/api/admin', () => ({ adminApi: api }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => authState }))
vi.mock('@/stores/ui', () => ({ useUiStore: () => ({ success: vi.fn(), err: vi.fn(), confirm: vi.fn() }) }))
vi.mock('@/stores/instance', () => ({ useInstanceStore: () => ({ invalidateCache: vi.fn() }) }))
vi.mock('@/utils/colorPalette', () => ({ applyTheme: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { slug: 'test' } }) }))

import Instance from './Instance.vue'

const settings = () => ({
  site_title: 'Fest', primary_color: '#123456', logo_filename: null,
  shifts_enabled: true, food_donations_enabled: true, site_locked: false, lock_message: null,
  registration_deadline: null, unregister_deadline_hours: null, updated_at: '2026-11-09T08:00:00',
})

beforeEach(() => {
  vi.clearAllMocks()
  authState.isAdmin = false
  api.getSiteSettings.mockResolvedValue({ data: { data: settings() } })
  api.updateSiteSettings.mockResolvedValue({ data: { data: { updated_at: '2026-11-09T09:00:00' } } })
})

describe('Instanz-Einstellungen', () => {
  it('Instanz-Admin sieht „Allgemein“, „Funktionen“ und „Einstellungen zurücksetzen“', async () => {
    authState.isInstanceAdminFor.mockReturnValue(true)
    render(Instance)
    expect(await screen.findByText('Funktionen')).toBeInTheDocument()
    expect(screen.getByText('Allgemein')).toBeInTheDocument()
    expect(screen.getByText('Einstellungen zurücksetzen')).toBeInTheDocument()
  })

  it('Organisator sieht nur „Funktionen“', async () => {
    authState.isInstanceAdminFor.mockReturnValue(false)
    render(Instance)
    expect(await screen.findByText('Funktionen')).toBeInTheDocument()
    expect(screen.queryByText('Allgemein')).not.toBeInTheDocument()
    expect(screen.queryByText('Einstellungen zurücksetzen')).not.toBeInTheDocument()
    expect(screen.queryByText('Gefahrenzone')).not.toBeInTheDocument()
  })

  it('Organisator sendet beim Speichern nur die Funktionen-Felder', async () => {
    authState.isInstanceAdminFor.mockReturnValue(false)
    render(Instance)
    await fireEvent.click(await screen.findByLabelText('Anmeldung gesperrt'))
    await fireEvent.click(screen.getByText('Speichern'))
    await waitFor(() => expect(api.updateSiteSettings).toHaveBeenCalled())
    const payload = api.updateSiteSettings.mock.calls[0][1]
    expect(payload.site_locked).toBe(true)
    expect(payload.updated_at).toBe('2026-11-09T08:00:00')
    expect(payload).not.toHaveProperty('site_title')
    expect(payload).not.toHaveProperty('primary_color')
  })

  it('Instanz-Admin sendet das komplette Formular', async () => {
    authState.isInstanceAdminFor.mockReturnValue(true)
    render(Instance)
    await screen.findByText('Funktionen')
    await fireEvent.click(screen.getByText('Speichern'))
    await waitFor(() => expect(api.updateSiteSettings).toHaveBeenCalled())
    expect(api.updateSiteSettings.mock.calls[0][1]).toHaveProperty('site_title', 'Fest')
  })
})
