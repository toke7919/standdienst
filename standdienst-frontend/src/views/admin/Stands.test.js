import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/vue'

const { api, ui } = vi.hoisted(() => ({
  api: {
    getStands: vi.fn(),
    createStand: vi.fn(),
    updateStand: vi.fn(),
    deleteStand: vi.fn(),
    reorderStands: vi.fn(),
  },
  ui: { success: vi.fn(), err: vi.fn(), confirm: vi.fn() },
}))

vi.mock('@/api/admin', () => ({ adminApi: api }))
vi.mock('@/stores/ui', () => ({ useUiStore: () => ui }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { slug: 'test' } }) }))

import Stands from './Stands.vue'

const LONG = 'Spätzle mit Soß und Kartoffelsalat'

beforeEach(() => {
  vi.clearAllMocks()
  api.getStands.mockResolvedValue({ data: { data: [{ id: 1, name: LONG, description: null }] } })
})

describe('Stände-Liste', () => {
  it('zeigt den Leerzustand ohne Stände', async () => {
    api.getStands.mockResolvedValue({ data: { data: [] } })
    render(Stands)
    expect(await screen.findByText('Noch keine Stände angelegt')).toBeInTheDocument()
  })

  it('Aktionen sind auch als reine Icons (mobil) per Name erreichbar', async () => {
    render(Stands)
    await screen.findByText(LONG)
    expect(screen.getByRole('button', { name: 'Bearbeiten' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Löschen' })).toBeInTheDocument()
  })

  it('kürzt den Namen mobil nicht ab, sondern bricht um', async () => {
    render(Stands)
    const name = await screen.findByText(LONG)
    expect(name.className).not.toMatch(/(^|\s)truncate(\s|$)/)
    expect(name.className).toMatch(/sm:truncate/)
  })

  it('Bearbeiten öffnet das Modal mit dem Namen', async () => {
    render(Stands)
    await fireEvent.click(await screen.findByRole('button', { name: 'Bearbeiten' }))
    expect(screen.getByText('Stand bearbeiten')).toBeInTheDocument()
    expect(screen.getByDisplayValue(LONG)).toBeInTheDocument()
  })
})
