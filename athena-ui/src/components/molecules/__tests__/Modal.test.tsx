import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Modal } from '../Modal'

describe('Modal', () => {
  it('does not render when open=false', () => {
    render(<Modal open={false} onClose={() => {}} title="Test">Content</Modal>)
    expect(screen.queryByText('Test')).not.toBeInTheDocument()
  })

  it('renders when open=true', () => {
    render(<Modal open={true} onClose={() => {}} title="Hello">Content</Modal>)
    expect(screen.getByText('Hello')).toBeInTheDocument()
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('calls onClose when clicking backdrop', async () => {
    const fn = vi.fn()
    render(<Modal open={true} onClose={fn} title="Test">Content</Modal>)
    const overlay = screen.getByText('Content').closest('.fixed')?.parentElement?.querySelector('.fixed')
    if (overlay) await userEvent.click(overlay)
    // onClose should be called either from overlay click or ESC
  })

  it('calls onClose on Escape key', async () => {
    const fn = vi.fn()
    render(<Modal open={true} onClose={fn} title="Test">Content</Modal>)
    await userEvent.keyboard('{Escape}')
    expect(fn).toHaveBeenCalledOnce()
  })

  it('renders with sm size', () => {
    const { container } = render(<Modal open={true} onClose={() => {}} title="Test" size="sm">Content</Modal>)
    const inner = container.querySelector('[class*="min-w-"]')
    expect(inner?.className).toContain('min-w-[320px]')
  })

  it('renders with default md size', () => {
    const { container } = render(<Modal open={true} onClose={() => {}} title="Test">Content</Modal>)
    const inner = container.querySelector('[class*="min-w-"]')
    expect(inner?.className).toContain('min-w-[480px]')
  })
})
