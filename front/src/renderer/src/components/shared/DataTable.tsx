import type { ReactNode } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@renderer/components/ui/table'

export interface DataColumn<T> {
  key: string
  title: ReactNode
  width?: number
  className?: string
  render: (record: T, index: number) => ReactNode
}

interface DataTableProps<T> {
  data: T[]
  columns: DataColumn<T>[]
  loading?: boolean
  rowKey: (record: T, index: number) => string
}

const DataTable = <T,>({
  data,
  columns,
  loading = false,
  rowKey
}: DataTableProps<T>) => {
  if (loading) {
    return (
      <div className="border-border bg-card text-muted-foreground flex h-full items-center justify-center rounded-2xl border shadow-[var(--shadow-lg)]">
        <div className="border-border bg-muted rounded-xl border px-5 py-3 font-medium">
          Loading data...
        </div>
      </div>
    )
  }

  if (!data.length) {
    return (
      <div className="border-border bg-card text-muted-foreground flex h-full items-center justify-center rounded-2xl border shadow-[var(--shadow-lg)]">
        <div className="border-border bg-muted rounded-xl border px-5 py-3 font-medium">
          No data
        </div>
      </div>
    )
  }

  return (
    <div className="border-border bg-card h-full overflow-auto rounded-2xl border p-3 shadow-[var(--shadow-lg)]">
      <Table>
        <TableHeader className="bg-muted sticky top-0 z-10">
          <TableRow>
            {columns.map((column) => (
              <TableHead
                key={column.key}
                className={column.className}
                style={{ minWidth: column.width }}
              >
                {column.title}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((record, index) => (
            <TableRow
              key={rowKey(record, index)}
              className={index % 2 ? 'bg-muted/35' : 'bg-transparent'}
            >
              {columns.map((column) => (
                <TableCell key={column.key} className={column.className}>
                  {column.render(record, index)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

export default DataTable
