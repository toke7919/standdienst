import { describe, it, expect, vi, beforeEach } from 'vitest'

const { setupState, authState } = vi.hoisted(() => ({
  setupState: { check: vi.fn(), maintenanceMode: false },
  authState: { isLoggedIn: true, isAdmin: false, isStaff: false, isVolunteer: false, user: {}, fetchMe: vi.fn() },
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
  authState.isAdmin = false
  authState.isStaff = false
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

describe('Router-Guard im Wartungsmodus', () => {
  beforeEach(async () => {
    setupState.check.mockResolvedValue(true)
    setupState.maintenanceMode = false
    await router.push('/impressum')
    setupState.maintenanceMode = true
  })

  it('leitet öffentliche Seiten auf /maintenance um und merkt sich das Ziel', async () => {
    await router.push('/fest/shifts')
    expect(router.currentRoute.value.path).toBe('/maintenance')
    expect(router.currentRoute.value.query.redirect).toBe('/fest/shifts')
  })

  it('leitet auch Organisatoren im Admin-Bereich um', async () => {
    authState.isStaff = true
    await router.push('/admin/dashboard')
    expect(router.currentRoute.value.path).toBe('/maintenance')
  })

  it('lässt Global-Admins in den Admin-Bereich', async () => {
    authState.isStaff = true
    authState.isAdmin = true
    await router.push('/admin/dashboard')
    expect(router.currentRoute.value.path).toBe('/admin/dashboard')
  })

  it('lässt den Admin-Login für alle offen', async () => {
    authState.isLoggedIn = false
    await router.push('/admin/login')
    expect(router.currentRoute.value.path).toBe('/admin/login')
  })
})

