import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/vue'

const { api, ui } = vi.hoisted(() => ({
  api: {
    getDates: vi.fn(),
    createDate: vi.fn(),
    updateDate: vi.fn(),
    duplicateDate: vi.fn(),
    deleteDate: vi.fn(),
  },
  ui: { success: vi.fn(), err: vi.fn(), confirm: vi.fn() },
}))

vi.mock('@/api/admin', () => ({ adminApi: api }))
vi.mock('@/stores/ui', () => ({ useUiStore: () => ui }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { slug: 'test' } }) }))

import Dates from './Dates.vue'

const DATE = { id: 1, date: '2026-12-06', formatted: 'Sonntag, 06.12.2026', label: 'Weihnachtsmarkt 2026', is_draft: false }

beforeEach(() => {
  vi.clearAllMocks()
  api.getDates.mockResolvedValue({ data: { data: [DATE] } })
})

describe('Termine-Liste', () => {
  it('zeigt den Leerzustand ohne Termine', async () => {
    api.getDates.mockResolvedValue({ data: { data: [] } })
    render(Dates)
    expect(await screen.findByText('Noch keine Termine angelegt')).toBeInTheDocument()
  })

  it('zeigt den Entwurf-Hinweis nur bei Entwürfen', async () => {
    api.getDates.mockResolvedValue({ data: { data: [DATE, { ...DATE, id: 2, formatted: 'Montag, 07.12.2026', is_draft: true }] } })
    render(Dates)
    await screen.findByText('Montag, 07.12.2026')
    expect(screen.getAllByText('Entwurf')).toHaveLength(1)
  })

  it('Aktionen sind auch als reine Icons (mobil) per Name erreichbar', async () => {
    render(Dates)
    await screen.findByText(DATE.formatted)
    for (const name of ['Bearbeiten', 'Duplizieren', 'Löschen']) {
      expect(screen.getByRole('button', { name })).toBeInTheDocument()
    }
  })

  it('Aktionsleiste schrumpft nicht und überlagert so den Text nicht', async () => {
    render(Dates)
    await screen.findByText(DATE.formatted)
    const actions = screen.getByRole('button', { name: 'Duplizieren' }).parentElement
    expect(actions.className).toMatch(/(^|\s)shrink-0(\s|$)/)
  })

  it('Bearbeiten öffnet das Modal', async () => {
    render(Dates)
    await fireEvent.click(await screen.findByRole('button', { name: 'Bearbeiten' }))
    expect(screen.getByText('Termin bearbeiten')).toBeInTheDocument()
  })
})
