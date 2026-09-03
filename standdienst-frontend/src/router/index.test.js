import { describe, it, expect, vi, beforeEach } from 'vitest'

const { setupState, authState } = vi.hoisted(() => ({
  setupState: { check: vi.fn(), maintenanceMode: false },
  authState: { isLoggedIn: true, isStaff: false, isVolunteer: false, user: {}, fetchMe: vi.fn() },
}))

vi.mock('@/stores/setup', () => ({ useSetupStore: () => setupState }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => authState }))
vi.mock('@/utils/colorPalette', () => ({ resetTheme: vi.fn() }))

// jsdom hat keine echte History-API-Basis – Memory-History erzwingen
vi.mock('vue-router', async (orig) => {
  const actual = await orig()
  return { ...actual, createWebHistory: actual.createMemoryHistory }
})

import router from './index'

beforeEach(() => {
  setupState.check.mockReset()
  setupState.maintenanceMode = false
  authState.isLoggedIn = true
  window.scrollTo = vi.fn() // jsdom implementiert scrollTo nicht
})

describe('Router-Guard', () => {
  it('leitet auf /setup um, solange Setup nicht abgeschlossen ist', async () => {
    setupState.check.mockResolvedValue(false)
    await router.push('/admin/login')
    expect(router.currentRoute.value.path).toBe('/setup')
  })

  it('lässt normale Seiten durch, wenn Setup abgeschlossen ist', async () => {
    setupState.check.mockResolvedValue(true)
    await router.push('/impressum')
    expect(router.currentRoute.value.path).toBe('/impressum')
  })

  it('tief verschachtelte unbekannte Pfade lösen die Catch-all-Route auf (NotFound)', async () => {
    setupState.check.mockResolvedValue(true)
    await router.push('/kein/bekannter/pfad/hier')
    const rec = router.currentRoute.value.matched[0]
    expect(rec.path).toBe('/:pathMatch(.*)*')
  })
})
