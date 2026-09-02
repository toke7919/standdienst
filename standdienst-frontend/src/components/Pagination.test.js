import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/vue'
import Pagination from './Pagination.vue'

describe('Pagination', () => {
  it('rendert nichts bei nur einer Seite', () => {
    const { container } = render(Pagination, {
      props: { page: 1, pages: 1, total: 5 },
    })
    expect(container).toBeEmptyDOMElement()
  })

  it('zeigt alle Seiten ohne Auslassung bei bis zu 7 Seiten', () => {
    render(Pagination, { props: { page: 1, pages: 7, total: 140 } })
    for (const n of [1, 2, 3, 4, 5, 6, 7]) {
      expect(screen.getByText(String(n))).toBeInTheDocument()
    }
    expect(screen.queryByText('…')).not.toBeInTheDocument()
  })

  it('zeigt Auslassung am Ende wenn die aktuelle Seite am Anfang steht', () => {
    render(Pagination, { props: { page: 1, pages: 20, total: 400 } })
    expect(screen.getAllByText('…')).toHaveLength(1)
    expect(screen.getByText('20')).toBeInTheDocument()
  })

  it('zeigt Auslassung am Anfang wenn die aktuelle Seite am Ende steht', () => {
    render(Pagination, { props: { page: 20, pages: 20, total: 400 } })
    expect(screen.getAllByText('…')).toHaveLength(1)
    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('zeigt Auslassung auf beiden Seiten wenn die aktuelle Seite in der Mitte steht', () => {
    render(Pagination, { props: { page: 10, pages: 20, total: 400 } })
    expect(screen.getAllByText('…')).toHaveLength(2)
  })

  it('emittiert update:page beim Klick auf eine Seitenzahl', async () => {
    const { emitted } = render(Pagination, { props: { page: 1, pages: 3, total: 60 } })
    await fireEvent.click(screen.getByText('2'))
    expect(emitted()['update:page'][0]).toEqual([2])
  })

  it('emittiert nichts beim Klick auf die Auslassung', async () => {
    const { emitted } = render(Pagination, { props: { page: 10, pages: 20, total: 400 } })
    const ellipsis = screen.getAllByText('…')[0]
    await fireEvent.click(ellipsis)
    expect(emitted()['update:page']).toBeUndefined()
  })
})
