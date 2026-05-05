import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { Icon } from '../Icon'

describe('Icon', () => {
  it('renders an SVG element', () => {
    const { container } = render(<Icon name="play" />)
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('applies custom size', () => {
    const { container } = render(<Icon name="play" size={24} />)
    const svg = container.querySelector('svg')
    expect(svg?.getAttribute('width')).toBe('24')
    expect(svg?.getAttribute('height')).toBe('24')
  })

  it('applies className', () => {
    const { container } = render(<Icon name="play" className="my-icon" />)
    const svg = container.querySelector('svg')
    expect(svg?.getAttribute('class')).toContain('my-icon')
  })

  it('renders known icons without error', () => {
    const icons = ['dashboard', 'chat', 'search', 'close', 'plus', 'pause', 'stop', 'refresh'] as const
    for (const name of icons) {
      const { container } = render(<Icon name={name} />)
      expect(container.querySelector('svg')).toBeInTheDocument()
    }
  })
})
