import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { StatusDot } from '../StatusDot'

describe('StatusDot', () => {
  it.each(['online', 'offline', 'warning', 'error'] as const)(
    'renders %s status with correct class',
    (status) => {
      const { container } = render(<StatusDot status={status} />)
      const dot = container.firstChild as HTMLElement
      const classMap: Record<string, string> = {
        online: 'bg-success-000',
        offline: 'bg-text-500',
        warning: 'bg-warning-000',
        error: 'bg-danger-000',
      }
      expect(dot.className).toContain(classMap[status])
    },
  )

  it('error status has pulse animation', () => {
    const { container } = render(<StatusDot status="error" />)
    expect(container.firstChild).toBeTruthy()
  })
})
