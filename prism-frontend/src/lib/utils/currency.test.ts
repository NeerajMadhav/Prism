import { describe, expect, it } from 'vitest';

import { formatCurrency } from '@/lib/utils/currency';

describe('formatCurrency', () => {
  it('formats standard amounts', () => {
    expect(formatCurrency(12.5, 'USD')).toContain('12.50');
  });

  it('uses compact notation for large values', () => {
    const compact = formatCurrency(1_200_000, 'USD', true);
    expect(compact.toLowerCase()).toMatch(/m|million|1\.2/i);
  });
});
