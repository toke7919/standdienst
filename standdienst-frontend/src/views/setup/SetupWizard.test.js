import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/vue'

const { api, markComplete } = vi.hoisted(() => ({
  api: {
    createAdmin: vi.fn(() => Promise.resolve({})),
    saveConfig: vi.fn(() => Promise.resolve({})),
    saveMail: vi.fn(() => Promise.resolve({})),
    finish: vi.fn(() => Promise.resolve({})),
  },
  markComplete: vi.fn(),
}))

vi.mock('@/api/setup', () => ({ setupApi: api }))
vi.mock('@/stores/setup', () => ({ useSetupStore: () => ({ markComplete }) }))

import SetupWizard from './SetupWizard.vue'

const renderWizard = () =>
  render(SetupWizard, { global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } })

const pwConfirmInput = () =>
  screen.getByText('Passwort bestätigen').parentElement.querySelector('input')

async function walkToMailStep() {
  await fireEvent.click(screen.getByText('Einrichtung starten'))
  await fireEvent.update(screen.getByPlaceholderText('admin@example.com'), 'admin@test.de')
  await fireEvent.update(screen.getByPlaceholderText('Mindestens 8 Zeichen'), 'Sicher!123456')
  await fireEvent.update(pwConfirmInput(), 'Sicher!123456')
  await fireEvent.click(screen.getByText('Weiter')) // Schritt 2 -> 3
  await fireEvent.click(screen.getByText('Weiter')) // Schritt 3 -> 4 (Mail)
}

beforeEach(() => vi.clearAllMocks())

describe('SetupWizard', () => {
  it('hat 4 Schritte und keinen GitHub-/PAT-Schritt', () => {
    renderWizard()
    expect(screen.getByText(/Schritt 1 von 4/)).toBeInTheDocument()
    expect(screen.queryByText(/GitHub/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Personal Access Token/i)).not.toBeInTheDocument()
  })

  it('schließt nach dem Mail-Schritt direkt ab (kein PAT-Schritt dazwischen)', async () => {
    renderWizard()
    await walkToMailStep()
    await fireEvent.click(screen.getByText(/Speichern & abschließen/))

    expect(api.saveMail).toHaveBeenCalledOnce()
    expect(api.finish).toHaveBeenCalledOnce()
    expect(markComplete).toHaveBeenCalledOnce()
    expect(await screen.findByText('Einrichtung abgeschlossen!')).toBeInTheDocument()
  })

  it('überspringt den Mail-Schritt und schließt direkt ab', async () => {
    renderWizard()
    await walkToMailStep()
    await fireEvent.click(screen.getByText(/Diesen Schritt überspringen/))

    expect(api.saveMail).not.toHaveBeenCalled()
    expect(api.finish).toHaveBeenCalledOnce()
    expect(await screen.findByText('Einrichtung abgeschlossen!')).toBeInTheDocument()
  })
})
