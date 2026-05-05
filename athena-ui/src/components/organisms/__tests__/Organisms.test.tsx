import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { PageHeader } from '../../organisms/PageHeader'
import { EmptyState } from '../../organisms/EmptyState'
import { DataTable } from '../../organisms/DataTable'
import { Button } from '../../atoms/Button'
import type { Column } from '../../organisms/DataTable'

describe('PageHeader', () => {
  it('renders title and subtitle', () => {
    render(<PageHeader title="Dashboard" subtitle="Overview" />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Overview')).toBeInTheDocument()
  })

  it('renders actions', () => {
    render(
      <PageHeader title="Title" actions={<Button>Action</Button>} />,
    )
    expect(screen.getByText('Action')).toBeInTheDocument()
  })
})

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No data" description="Nothing to show" />)
    expect(screen.getByText('No data')).toBeInTheDocument()
    expect(screen.getByText('Nothing to show')).toBeInTheDocument()
  })

  it('renders action', () => {
    render(
      <EmptyState title="Empty" action={<Button>Retry</Button>} />,
    )
    expect(screen.getByText('Retry')).toBeInTheDocument()
  })
})

describe('DataTable', () => {
  const columns: readonly Column<{ id: string; name: string }>[] = [
    { key: 'id', header: 'ID', render: (r) => r.id },
    { key: 'name', header: 'Name', render: (r) => r.name },
  ]

  const data = [
    { id: '1', name: 'Alice' },
    { id: '2', name: 'Bob' },
  ]

  it('renders headers and rows', () => {
    render(
      <MemoryRouter>
        <DataTable columns={columns} data={data} />
      </MemoryRouter>,
    )
    expect(screen.getByText('ID')).toBeInTheDocument()
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Alice')).toBeInTheDocument()
    expect(screen.getByText('Bob')).toBeInTheDocument()
  })

  it('shows empty state when no data', () => {
    render(
      <MemoryRouter>
        <DataTable columns={columns} data={[]} />
      </MemoryRouter>,
    )
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })
})
