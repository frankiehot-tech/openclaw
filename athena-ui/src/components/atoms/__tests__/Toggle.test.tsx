import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Toggle } from '../Toggle'

describe('Toggle', () => {
  it('renders unchecked by default', () => {
    render(<Toggle checked={false} onChange={() => {}} />)
    const toggle = screen.getByRole('switch')
    expect(toggle).not.toBeChecked()
  })

  it('renders checked', () => {
    render(<Toggle checked={true} onChange={() => {}} />)
    const toggle = screen.getByRole('switch')
    expect(toggle).toBeChecked()
  })

  it('calls onChange with true when toggled on', async () => {
    const fn = vi.fn()
    render(<Toggle checked={false} onChange={fn} />)
    await userEvent.click(screen.getByRole('switch'))
    expect(fn).toHaveBeenCalledWith(true)
  })

  it('calls onChange with false when toggled off', async () => {
    const fn = vi.fn()
    render(<Toggle checked={true} onChange={fn} />)
    await userEvent.click(screen.getByRole('switch'))
    expect(fn).toHaveBeenCalledWith(false)
  })

  it('applies brand color when checked', () => {
    render(<Toggle checked={true} onChange={() => {}} />)
    const toggle = screen.getByRole('switch')
    expect(toggle.className).toContain('bg-brand-000')
  })

  it('does not toggle when disabled', async () => {
    const fn = vi.fn()
    render(<Toggle checked={false} onChange={fn} disabled />)
    await userEvent.click(screen.getByRole('switch'))
    expect(fn).not.toHaveBeenCalled()
  })
})
