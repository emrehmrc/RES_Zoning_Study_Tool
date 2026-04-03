'use client'

import { useMemo, useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table'

interface Props {
  columns: string[]
  data: any[]
  onRowClick?: (rowData: any) => void
}

export default function AnalysisResultsTable({ columns: colNames, data, onRowClick }: Props) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [pageIndex, setPageIndex] = useState(0)
  const [pageSize, setPageSize] = useState(25)

  const columns = useMemo<ColumnDef<any, any>[]>(() => {
    const helper = createColumnHelper<any>()
    return colNames.map(col =>
      helper.accessor(col, {
        header: col,
        cell: info => {
          const v = info.getValue()
          if (typeof v === 'number') return Math.round(v * 1000) / 1000
          if (typeof v === 'string' && v.length > 60) return v.slice(0, 60) + '…'
          return v
        },
        filterFn: 'includesString',
      })
    )
  }, [colNames])

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnFilters, pagination: { pageIndex, pageSize } },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: (updater) => {
      const next = typeof updater === 'function' ? updater({ pageIndex, pageSize }) : updater
      setPageIndex(next.pageIndex)
      setPageSize(next.pageSize)
    },
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="space-y-3">
      {/* Controls row */}
      <div className="flex items-center justify-between text-sm text-slate-600">
        <div className="flex items-center gap-2">
          <span>Show</span>
          <select
            value={pageSize}
            onChange={e => { setPageSize(Number(e.target.value)); setPageIndex(0) }}
            className="border rounded px-2 py-1 text-sm"
          >
            {[10, 25, 50, 100].map(n => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
          <span>rows</span>
        </div>
        <span className="text-xs text-slate-400">
          {table.getFilteredRowModel().rows.length} of {data.length} rows
          {table.getFilteredRowModel().rows.length !== data.length && ' (filtered)'}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border rounded-lg">
        <table className="min-w-full text-xs">
          <thead className="bg-slate-100">
            {table.getHeaderGroups().map(hg => (
              <tr key={hg.id}>
                {hg.headers.map(header => (
                  <th key={header.id} className="px-2 py-1.5 text-center font-medium text-slate-600 whitespace-nowrap">
                    <div
                      className={header.column.getCanSort() ? 'cursor-pointer select-none flex items-center justify-center gap-1' : ''}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{ asc: ' ▲', desc: ' ▼' }[header.column.getIsSorted() as string] ?? ''}
                    </div>
                    {/* Column filter */}
                    <input
                      type="text"
                      value={(header.column.getFilterValue() as string) ?? ''}
                      onChange={e => header.column.setFilterValue(e.target.value)}
                      placeholder="Filter…"
                      className="mt-1 w-full border rounded px-1 py-0.5 text-xs font-normal text-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-300"
                    />
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y">
            {table.getRowModel().rows.map(row => (
              <tr key={row.id} className={`hover:bg-slate-50 ${onRowClick ? 'cursor-pointer' : ''}`}
                onClick={() => { if (onRowClick) onRowClick(row.original) }}
              >
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-2 py-1 text-slate-700 whitespace-nowrap text-center">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex gap-1">
          <button
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
            className="px-2 py-1 border rounded disabled:opacity-30 hover:bg-slate-100"
          >«</button>
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-2 py-1 border rounded disabled:opacity-30 hover:bg-slate-100"
          >‹</button>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-2 py-1 border rounded disabled:opacity-30 hover:bg-slate-100"
          >›</button>
          <button
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
            className="px-2 py-1 border rounded disabled:opacity-30 hover:bg-slate-100"
          >»</button>
        </div>
        <span className="text-xs text-slate-500">
          Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
        </span>
      </div>
    </div>
  )
}
