import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Tag } from '../Tag'

describe('Tag', () => {
  it('renders children', () => {
    render(<Tag>Active</Tag>)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('applies default color', () => {
    render(<Tag>Default</Tag>)
    const tag = screen.getByText('Default')
    expect(tag.className).toContain('bg-bg-300')
  })

  it('applies success color', () => {
    render(<Tag color="success">Success</Tag>)
    const tag = screen.getByText('Success')
    expect(tag.className).toContain('bg-success-000')
  })

  it('applies warning color', () => {
    render(<Tag color="warning">Warning</Tag>)
    const tag = screen.getByText('Warning')
    expect(tag.className).toContain('bg-warning-000')
  })

  it('applies danger color', () => {
    render(<Tag color="danger">Danger</Tag>)
    const tag = screen.getByText('Danger')
    expect(tag.className).toContain('bg-danger-000')
  })

  it('applies brand color', () => {
    render(<Tag color="brand">Brand</Tag>)
    const tag = screen.getByText('Brand')
    expect(tag.className).toContain('bg-brand-000')
  })

  it('passes className through', () => {
    render(<Tag className="custom-tag">Custom</Tag>)
    const tag = screen.getByText('Custom')
    expect(tag.className).toContain('custom-tag')
  })
})
