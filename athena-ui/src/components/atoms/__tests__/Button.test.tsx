import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from '../Button'

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('calls onClick handler', async () => {
    const fn = vi.fn()
    render(<Button onClick={fn}>Click</Button>)
    await userEvent.click(screen.getByText('Click'))
    expect(fn).toHaveBeenCalledOnce()
  })

  it('shows primary variant styles', () => {
    render(<Button variant="primary">Primary</Button>)
    const btn = screen.getByText('Primary')
    expect(btn.className).toContain('bg-brand-000')
  })

  it('shows secondary variant styles', () => {
    render(<Button variant="secondary">Secondary</Button>)
    const btn = screen.getByText('Secondary')
    expect(btn.className).toContain('bg-bg-200')
  })

  it('shows danger variant styles', () => {
    render(<Button variant="danger">Danger</Button>)
    const btn = screen.getByText('Danger')
    expect(btn.className).toContain('bg-danger-000')
  })

  it('applies sm size class', () => {
    render(<Button size="sm">Small</Button>)
    const btn = screen.getByText('Small')
    expect(btn.className).toContain('px-2.5')
  })

  it('applies lg size class', () => {
    render(<Button size="lg">Large</Button>)
    const btn = screen.getByText('Large')
    expect(btn.className).toContain('px-6')
  })

  it('disables click when disabled', () => {
    const fn = vi.fn()
    render(<Button disabled onClick={fn}>Disabled</Button>)
    const btn = screen.getByText('Disabled')
    expect(btn).toBeDisabled()
  })

  it('disables click when loading', () => {
    render(<Button loading>Loading</Button>)
    const btn = screen.getByText('Loading')
    expect(btn).toBeDisabled()
  })

  it('passes className through', () => {
    render(<Button className="my-custom">Custom</Button>)
    const btn = screen.getByText('Custom')
    expect(btn.className).toContain('my-custom')
  })
})
