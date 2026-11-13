/** PRISM FinOps — adapters from live FastAPI response shapes to UI types. */

import type { Paginated } from '@/types/api';

/** Backend list envelope: `{ data, pagination: { total, page, limit, pages } }`. */
export interface BackendPaginated<T> {
  data: T[];
  pagination: {
    total: number;
    page: number;
    limit: number;
    pages: number;
  };
}

/** Converts backend pagination into the frontend `Paginated<T>` shape. */
export function normalizePaginated<T>(payload: BackendPaginated<T> | Paginated<T> | T[]): Paginated<T> {
  if (Array.isArray(payload)) {
    return { items: payload, total: payload.length, page: 1, size: payload.length || 20 };
  }
  if ('items' in payload && Array.isArray(payload.items)) {
    return payload;
  }
  const backend = payload as BackendPaginated<T>;
  return {
    items: backend.data ?? [],
    total: backend.pagination?.total ?? 0,
    page: backend.pagination?.page ?? 1,
    size: backend.pagination?.limit ?? 20,
  };
}

/** Computes MoM percent from current vs previous totals. */
export function computeMomPct(current: number, previous: number): number | null {
  if (!previous) {
    return current === 0 ? 0 : null;
  }
  return ((current - previous) / previous) * 100;
}
