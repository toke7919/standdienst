import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const { api } = vi.hoisted(() => ({ api: { status: vi.fn() } }))
vi.mock('@/api/setup', () => ({ setupApi: api }))

import { useSetupStore } from './setup'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('Setup-Store check()', () => {
  it('übernimmt Setup- und Wartungsstatus aus der API', async () => {
    api.status.mockResolvedValue({ data: { data: { setup_complete: true, maintenance_mode: true } } })
    const setup = useSetupStore()
    expect(await setup.check()).toBe(true)
    expect(setup.maintenanceMode).toBe(true)
  })

  it('API nicht erreichbar (502) → Wartungsmodus, Setup nicht blockieren', async () => {
    api.status.mockRejectedValue({ response: { status: 502 } })
    const setup = useSetupStore()
    expect(await setup.check()).toBe(true)
    expect(setup.maintenanceMode).toBe(true)
  })

  it('sonstiger Fehler (500) → kein Wartungsmodus', async () => {
    api.status.mockRejectedValue({ response: { status: 500 } })
    const setup = useSetupStore()
    expect(await setup.check()).toBe(true)
    expect(setup.maintenanceMode).toBe(false)
  })
})
