import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/vue'

const { api, setupState, authState, routeState } = vi.hoisted(() => ({
  api: { status: vi.fn() },
  setupState: { setMaintenance: vi.fn() },
  authState: { isAdmin: false },
  routeState: { query: {} },
}))

vi.mock('@/api/setup', () => ({ setupApi: api }))
vi.mock('@/stores/setup', () => ({ useSetupStore: () => setupState }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => authState }))
vi.mock('vue-router', () => ({ useRoute: () => routeState }))

import Maintenance from './Maintenance.vue'

const statusOk = (maintenance_mode) =>
  api.status.mockResolvedValue({ data: { data: { setup_complete: true, maintenance_mode } } })

let replace
beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  authState.isAdmin = false
  routeState.query = {}
  replace = vi.fn()
  Object.defineProperty(window, 'location', { value: { replace }, writable: true, configurable: true })
})
afterEach(() => vi.useRealTimers())

async function tick() {
  await vi.advanceTimersByTimeAsync(5000)
}

describe('Wartungsseite', () => {
  it('zeigt den Wartungshinweis', () => {
    statusOk(true)
    render(Maintenance)
    expect(screen.getByText(/befindet sich gerade im Wartungsmodus/)).toBeInTheDocument()
    expect(screen.getByText(/in wenigen Augenblicken wieder verfügbar/)).toBeInTheDocument()
  })

  it('lädt die ursprüngliche Seite neu, sobald die Wartung beendet ist', async () => {
    routeState.query = { redirect: '/fest/shifts' }
    statusOk(false)
    render(Maintenance)
    await tick()
    expect(setupState.setMaintenance).toHaveBeenCalledWith(false)
    expect(replace).toHaveBeenCalledWith('/fest/shifts')
  })

  it('bleibt, solange die Wartung läuft', async () => {
    statusOk(true)
    render(Maintenance)
    await tick()
    await tick()
    expect(replace).not.toHaveBeenCalled()
  })

  it('bleibt, solange die API nicht erreichbar ist', async () => {
    api.status.mockRejectedValue({ request: {}, code: 'ERR_NETWORK' })
    render(Maintenance)
    await tick()
    expect(replace).not.toHaveBeenCalled()
  })

  it('Global-Admin kehrt bei laufender Wartung in den Admin-Bereich zurück', async () => {
    authState.isAdmin = true
    routeState.query = { redirect: '/admin/dashboard' }
    statusOk(true)
    render(Maintenance)
    await tick()
    expect(replace).toHaveBeenCalledWith('/admin/dashboard')
  })

  it('folgt keinen externen Weiterleitungszielen', async () => {
    routeState.query = { redirect: '//evil.example.com' }
    statusOk(false)
    render(Maintenance)
    await tick()
    expect(replace).toHaveBeenCalledWith('/')
  })
})
