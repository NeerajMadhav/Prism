import { describe, expect, it } from 'vitest';

import { computeMomPct, normalizePaginated } from '@/lib/api/normalize';

describe('normalizePaginated', () => {
  it('maps backend {data,pagination} to {items,total,page,size}', () => {
    const result = normalizePaginated({
      data: [{ id: '1' }],
      pagination: { total: 1, page: 2, limit: 20, pages: 1 },
    });
    expect(result).toEqual({
      items: [{ id: '1' }],
      total: 1,
      page: 2,
      size: 20,
    });
  });

  it('passes through already-normalized payloads', () => {
    const result = normalizePaginated({
      items: [{ id: 'x' }],
      total: 1,
      page: 1,
      size: 10,
    });
    expect(result.items[0]?.id).toBe('x');
  });

  it('wraps bare arrays', () => {
    expect(normalizePaginated([{ a: 1 }]).total).toBe(1);
  });
});

describe('computeMomPct', () => {
  it('returns percent change', () => {
    expect(computeMomPct(110, 100)).toBeCloseTo(10);
  });

  it('returns null when previous is zero and current positive', () => {
    expect(computeMomPct(10, 0)).toBeNull();
  });
});
