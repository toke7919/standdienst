import { describe, it, expect } from 'vitest'
import { isApiUnavailable, mayBypassMaintenance } from './maintenance'

describe('isApiUnavailable', () => {
  it.each([502, 503, 504])('HTTP %i gilt als nicht erreichbar', (status) => {
    expect(isApiUnavailable({ response: { status } })).toBe(true)
  })

  it.each([400, 401, 403, 404, 409, 500])('HTTP %i ist ein normaler Fehler', (status) => {
    expect(isApiUnavailable({ response: { status } })).toBe(false)
  })

  it('Netzwerkfehler ohne Antwort gilt als nicht erreichbar', () => {
    expect(isApiUnavailable({ code: 'ERR_NETWORK', request: {} })).toBe(true)
  })

  it('abgebrochene Anfrage ist kein Ausfall', () => {
    expect(isApiUnavailable({ code: 'ERR_CANCELED', request: {} })).toBe(false)
  })

  it('Fehler ohne Request (z. B. Programmfehler) ist kein Ausfall', () => {
    expect(isApiUnavailable(new Error('kaputt'))).toBe(false)
  })
})

describe('mayBypassMaintenance', () => {
  it('Admin-Login und 2FA sind für alle erreichbar', () => {
    expect(mayBypassMaintenance('/admin/login', false)).toBe(true)
    expect(mayBypassMaintenance('/admin/login/2fa', false)).toBe(true)
  })

  it('Admin-Bereich nur für Global-Admins', () => {
    expect(mayBypassMaintenance('/admin/dashboard', true)).toBe(true)
    expect(mayBypassMaintenance('/admin/dashboard', false)).toBe(false)
    expect(mayBypassMaintenance('/admin/fest/settings', false)).toBe(false)
  })

  it('öffentliche und Helfer-Seiten nie', () => {
    expect(mayBypassMaintenance('/', true)).toBe(false)
    expect(mayBypassMaintenance('/fest/shifts', true)).toBe(false)
    expect(mayBypassMaintenance('/administration', true)).toBe(false)
  })
})
