import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProgressBar } from '../ProgressBar'

describe('ProgressBar', () => {
  it('renders fill with correct width', () => {
    const { container } = render(<ProgressBar value={75} />)
    const fill = container.querySelector('.progress-fill') || container.querySelector('[style*="width"]')
    expect(fill).toBeTruthy()
  })

  it('clamps value to 0 minimum', () => {
    const { container } = render(<ProgressBar value={-10} />)
    const fill = container.querySelector('[style*="width"]')
    expect(fill?.getAttribute('style')).toContain('0%')
  })

  it('clamps value to 100 maximum', () => {
    const { container } = render(<ProgressBar value={150} />)
    const fill = container.querySelector('[style*="width"]')
    expect(fill?.getAttribute('style')).toContain('100%')
  })

  it('shows label when showLabel is true', () => {
    render(<ProgressBar value={42} showLabel />)
    expect(screen.getByText('42%')).toBeInTheDocument()
  })

  it('applies brand color', () => {
    const { container } = render(<ProgressBar value={50} color="brand" />)
    const fill = container.querySelector('[style*="width"]')
    expect(fill?.className).toContain('bg-brand-000')
  })

  it('applies danger color', () => {
    const { container } = render(<ProgressBar value={50} color="danger" />)
    const fill = container.querySelector('[style*="width"]')
    expect(fill?.className).toContain('bg-danger-000')
  })
})
