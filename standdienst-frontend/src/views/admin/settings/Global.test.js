import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/vue'

const { api } = vi.hoisted(() => ({
  api: { getGlobalSettings: vi.fn(), updateGlobalSettings: vi.fn() },
}))

vi.mock('@/api/admin', () => ({ adminApi: api }))
vi.mock('@/stores/ui', () => ({ useUiStore: () => ({ success: vi.fn(), err: vi.fn() }) }))

import Global from './Global.vue'

const settings = (extra = {}) => ({
  base_url: null, copyright_text: null, timezone: 'Europe/Berlin', log_retention_months: 3,
  volunteer_retention_months: null, ip_whitelist: null, trusted_proxies: null,
  updated_at: '2026-11-10T08:00:00', ...extra,
})

const proxyField = () => screen.getByLabelText(/Vertrauenswürdige Reverse-Proxys/)

beforeEach(() => {
  vi.clearAllMocks()
  api.getGlobalSettings.mockResolvedValue({ data: { data: settings() } })
  api.updateGlobalSettings.mockResolvedValue({ data: { data: { updated_at: '2026-11-10T09:00:00' } } })
})

describe('Globale Einstellungen – vertrauenswürdige Reverse-Proxys', () => {
  it('zeigt den gespeicherten Wert', async () => {
    api.getGlobalSettings.mockResolvedValue({ data: { data: settings({ trusted_proxies: '10.0.0.5' }) } })
    render(Global)
    await screen.findByText('Sicherheit')
    expect(proxyField().value).toBe('10.0.0.5')
  })

  it('normalisiert die Eingabe und sendet sie beim Speichern mit', async () => {
    render(Global)
    await screen.findByText('Sicherheit')
    await fireEvent.update(proxyField(), '10.0.0.5\n172.18.0.0/16')
    await fireEvent.blur(proxyField())
    expect(proxyField().value).toBe('10.0.0.5, 172.18.0.0/16')
    await fireEvent.click(screen.getByRole('button', { name: /Speichern/ }))
    await waitFor(() => expect(api.updateGlobalSettings).toHaveBeenCalled())
    expect(api.updateGlobalSettings.mock.calls[0][0].trusted_proxies).toBe('10.0.0.5, 172.18.0.0/16')
  })

  it('zeigt die Validierungsmeldung des Backends am Feld', async () => {
    api.updateGlobalSettings.mockRejectedValue({
      response: { data: { error: 'Validierungsfehler', errors: { trusted_proxies: ['Netz zu weit: 0.0.0.0/0'] } } },
    })
    render(Global)
    await screen.findByText('Sicherheit')
    await fireEvent.update(proxyField(), '0.0.0.0/0')
    await fireEvent.click(screen.getByRole('button', { name: /Speichern/ }))
    expect(await screen.findByText('Netz zu weit: 0.0.0.0/0')).toBeInTheDocument()
  })
})
