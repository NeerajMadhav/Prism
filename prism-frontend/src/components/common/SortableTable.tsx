/** PRISM FinOps — client-side sortable data table. */

'use client';

import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { EmptyState } from '@/components/common/EmptyState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';

export interface SortableColumn<T> {
  key: keyof T | string;
  label: string;
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
  render?: (row: T) => ReactNode;
}

interface SortableTableProps<T extends Record<string, unknown>> {
  columns: SortableColumn<T>[];
  data: T[];
  keyField: keyof T;
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyState?: ReactNode;
  className?: string;
}

type SortDir = 'asc' | 'desc';

function cellValue<T>(row: T, key: keyof T | string): unknown {
  return (row as Record<string, unknown>)[String(key)];
}

/** Table with optional client-side sort and loading skeleton rows. */
export function SortableTable<T extends Record<string, unknown>>({
  columns,
  data,
  keyField,
  onRowClick,
  loading,
  emptyState,
  className,
}: SortableTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const sorted = useMemo(() => {
    if (!sortKey) {
      return data;
    }
    const copy = [...data];
    copy.sort((a, b) => {
      const av = cellValue(a, sortKey);
      const bv = cellValue(b, sortKey);
      if (av === bv) {
        return 0;
      }
      if (av == null) {
        return 1;
      }
      if (bv == null) {
        return -1;
      }
      const cmp = av > bv ? 1 : -1;
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [data, sortDir, sortKey]);

  const toggleSort = (key: string, sortable?: boolean) => {
    if (!sortable) {
      return;
    }
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  if (loading) {
    return <LoadingSkeleton variant="table" />;
  }

  if (!sorted.length) {
    return emptyState ?? <EmptyState title="No data" message="Nothing to show yet." />;
  }

  return (
    <div className={cn('rounded-lg border', className)}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((col) => {
              const active = sortKey === String(col.key);
              return (
                <TableHead
                  key={String(col.key)}
                  className={cn(
                    col.sortable && 'cursor-pointer select-none',
                    col.align === 'right' && 'text-right',
                    col.align === 'center' && 'text-center',
                  )}
                  onClick={() => toggleSort(String(col.key), col.sortable)}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {col.sortable ? (
                      active ? (
                        sortDir === 'asc' ? (
                          <ArrowUp className="size-3.5" />
                        ) : (
                          <ArrowDown className="size-3.5" />
                        )
                      ) : (
                        <ArrowUpDown className="size-3.5 opacity-40" />
                      )
                    ) : null}
                  </span>
                </TableHead>
              );
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((row) => (
            <TableRow
              key={String(row[keyField])}
              className={onRowClick ? 'cursor-pointer' : undefined}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((col) => (
                <TableCell
                  key={String(col.key)}
                  className={cn(
                    col.align === 'right' && 'text-right',
                    col.align === 'center' && 'text-center',
                  )}
                >
                  {col.render
                    ? col.render(row)
                    : String(cellValue(row, col.key) ?? '—')}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
