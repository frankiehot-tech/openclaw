import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SearchBox } from '../SearchBox'

describe('SearchBox', () => {
  it('renders with placeholder', () => {
    render(<SearchBox value="" onChange={() => {}} placeholder="Search..." />)
    expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument()
  })

  it('calls onChange on input', async () => {
    const fn = vi.fn()
    render(<SearchBox value="" onChange={fn} />)
    await userEvent.type(screen.getByRole('textbox'), 'test')
    expect(fn).toHaveBeenCalledTimes(4)
  })

  it('displays current value', () => {
    render(<SearchBox value="hello" onChange={() => {}} />)
    expect(screen.getByDisplayValue('hello')).toBeInTheDocument()
  })
})
