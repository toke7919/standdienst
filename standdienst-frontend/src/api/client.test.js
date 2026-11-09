import { describe, it, expect, vi, afterEach } from 'vitest'
import client from './client'

const rejected = client.interceptors.response.handlers[0].rejected

afterEach(() => vi.restoreAllMocks())

describe('API-Client', () => {
  it('meldet „api:unavailable“, wenn die API nicht erreichbar ist (502)', async () => {
    const spy = vi.spyOn(window, 'dispatchEvent')
    const err = { config: {}, response: { status: 502 } }
    await expect(rejected(err)).rejects.toBe(err)
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ type: 'api:unavailable' }))
  })

  it('meldet nichts bei normalen Fehlern (404)', async () => {
    const spy = vi.spyOn(window, 'dispatchEvent')
    const err = { config: {}, response: { status: 404 } }
    await expect(rejected(err)).rejects.toBe(err)
    expect(spy).not.toHaveBeenCalled()
  })
})
