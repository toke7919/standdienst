import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUiStore } from './ui'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.useFakeTimers()
})

describe('useUiStore', () => {
  it('fügt einen Toast hinzu und entfernt ihn nach der Dauer', () => {
    const ui = useUiStore()
    ui.success('gespeichert')
    expect(ui.toasts).toHaveLength(1)
    expect(ui.toasts[0]).toMatchObject({ message: 'gespeichert', type: 'success' })

    vi.advanceTimersByTime(4000)
    expect(ui.toasts).toHaveLength(0)
  })

  it('err-Toast bleibt 6s statt 4s', () => {
    const ui = useUiStore()
    ui.err('kaputt')
    vi.advanceTimersByTime(4000)
    expect(ui.toasts).toHaveLength(1)
    vi.advanceTimersByTime(2000)
    expect(ui.toasts).toHaveLength(0)
  })

  it('confirm() löst mit dem an closeConfirm übergebenen Ergebnis auf', async () => {
    const ui = useUiStore()
    const answer = ui.confirm({ title: 'Sicher?' })
    expect(ui.confirmDialog).toMatchObject({ title: 'Sicher?' })

    ui.closeConfirm(true)
    await expect(answer).resolves.toBe(true)
    expect(ui.confirmDialog).toBeNull()
  })
})
