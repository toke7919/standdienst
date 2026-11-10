import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/vue'
import RowAction from './RowAction.vue'

describe('RowAction', () => {
  it.each([
    ['edit', 'Bearbeiten'],
    ['duplicate', 'Duplizieren'],
    ['delete', 'Löschen'],
  ])('%s: Standardbeschriftung als Text (Desktop) und zugänglicher Name (Icon mobil)', (action, label) => {
    render(RowAction, { props: { action } })
    const btn = screen.getByRole('button', { name: label })
    expect(btn).toHaveTextContent(label)
    expect(btn.querySelector('svg')).not.toBeNull()
  })

  it('Text ist nur ab sm sichtbar, Icon nur darunter', () => {
    render(RowAction, { props: { action: 'edit' } })
    const btn = screen.getByRole('button', { name: 'Bearbeiten' })
    expect(btn.querySelector('span').className).toMatch(/hidden sm:inline/)
    expect(btn.querySelector('svg').getAttribute('class')).toMatch(/sm:hidden/)
  })

  it('eigene Beschriftung überschreibt die Standardbeschriftung', () => {
    render(RowAction, { props: { action: 'delete', label: 'Entfernen' } })
    expect(screen.getByRole('button', { name: 'Entfernen' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Löschen' })).toBeNull()
  })

  it('löst beim Klick das click-Event aus', async () => {
    const { emitted } = render(RowAction, { props: { action: 'edit' } })
    await fireEvent.click(screen.getByRole('button'))
    expect(emitted().click).toHaveLength(1)
  })

  it('deaktiviert: kein Klick, Hinweis als title', async () => {
    let clicks = 0
    render(RowAction, {
      props: { action: 'delete', disabled: true, title: 'Primärer Admin ist löschgeschützt' },
      attrs: { onClick: () => clicks++ },
    })
    const btn = screen.getByRole('button', { name: 'Löschen' })
    expect(btn).toBeDisabled()
    expect(btn).toHaveAttribute('title', 'Primärer Admin ist löschgeschützt')
    await fireEvent.click(btn)
    expect(clicks).toBe(0)
  })

  it('ist kein Submit-Button (sicher in Formularen)', () => {
    render(RowAction, { props: { action: 'edit' } })
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button')
  })
})
