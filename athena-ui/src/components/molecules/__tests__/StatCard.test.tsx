import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatCard } from '../StatCard'

describe('StatCard', () => {
  it('renders label and value', () => {
    render(<StatCard label="CPU" value="72%" />)
    expect(screen.getByText('CPU')).toBeInTheDocument()
    expect(screen.getByText('72%')).toBeInTheDocument()
  })

  it('renders up trend', () => {
    render(<StatCard label="CPU" value="72%" trend="+5%" trendDirection="up" />)
    expect(screen.getByText(/\+5%/)).toBeInTheDocument()
  })

  it('renders down trend', () => {
    render(<StatCard label="CPU" value="72%" trend="-5%" trendDirection="down" />)
    expect(screen.getByText(/-5%/)).toBeInTheDocument()
  })
})
