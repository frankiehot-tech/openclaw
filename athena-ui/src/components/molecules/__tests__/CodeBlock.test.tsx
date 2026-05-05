import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CodeBlock } from '../CodeBlock'

describe('CodeBlock', () => {
  it('renders code content', () => {
    render(<CodeBlock code="console.log('hello')" />)
    expect(screen.getByText("console.log('hello')")).toBeInTheDocument()
  })

  it('shows language header', () => {
    render(<CodeBlock code="const x = 1" language="typescript" />)
    expect(screen.getByText('typescript')).toBeInTheDocument()
  })

  it('shows line numbers when enabled', () => {
    render(<CodeBlock code={'line1\nline2'} showLineNumbers />)
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })
})
