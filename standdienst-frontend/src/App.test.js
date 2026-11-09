import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/vue'

const { api, setupState, authState, routerState, routeState } = vi.hoisted(() => ({
  api: { status: vi.fn() },
  setupState: { maintenanceMode: false, setMaintenance: vi.fn() },
  authState: { isAdmin: false },
  routerState: { push: vi.fn() },
  routeState: { path: '/fest/shifts', fullPath: '/fest/shifts', meta: {} },
}))

vi.mock('@/api/setup', () => ({ setupApi: api }))
vi.mock('@/stores/setup', () => ({ useSetupStore: () => setupState }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => authState }))
vi.mock('vue-router', () => ({
  useRouter: () => routerState,
  useRoute: () => routeState,
  RouterView: { template: '<div />' },
}))

import App from './App.vue'

beforeEach(() => {
  vi.clearAllMocks()
  authState.isAdmin = false
  routeState.path = '/fest/shifts'
  routeState.fullPath = '/fest/shifts'
  routeState.meta = {}
})

describe('App – API nicht erreichbar', () => {
  it('schaltet auf die Wartungsseite und merkt sich die aktuelle Seite', () => {
    render(App, { global: { stubs: { ToastContainer: true } } })
    window.dispatchEvent(new CustomEvent('api:unavailable'))
    expect(setupState.setMaintenance).toHaveBeenCalledWith(true)
    expect(routerState.push).toHaveBeenCalledWith({ path: '/maintenance', query: { redirect: '/fest/shifts' } })
  })

  it('leitet auch Global-Admins um (die API ist ja weg)', () => {
    authState.isAdmin = true
    routeState.path = routeState.fullPath = '/admin/dashboard'
    render(App, { global: { stubs: { ToastContainer: true } } })
    window.dispatchEvent(new CustomEvent('api:unavailable'))
    expect(routerState.push).toHaveBeenCalledWith({ path: '/maintenance', query: { redirect: '/admin/dashboard' } })
  })

  it('bleibt auf der Wartungsseite, wenn sie schon angezeigt wird', () => {
    routeState.meta = { maintenance: true }
    render(App, { global: { stubs: { ToastContainer: true } } })
    window.dispatchEvent(new CustomEvent('api:unavailable'))
    expect(routerState.push).not.toHaveBeenCalled()
  })
})
