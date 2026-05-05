import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LogEntry } from '../LogEntry'

describe('LogEntry', () => {
  it('renders time, level, and message', () => {
    render(<LogEntry time="14:32:01" level="info" message="Server started" />)
    expect(screen.getByText('14:32:01')).toBeInTheDocument()
    expect(screen.getByText('INFO')).toBeInTheDocument()
    expect(screen.getByText('Server started')).toBeInTheDocument()
  })

  it('renders warn level', () => {
    render(<LogEntry time="14:32:01" level="warn" message="Warning" />)
    expect(screen.getByText('WARN')).toBeInTheDocument()
  })

  it('renders error level', () => {
    render(<LogEntry time="14:32:01" level="error" message="Error" />)
    expect(screen.getByText('ERROR')).toBeInTheDocument()
  })
})
