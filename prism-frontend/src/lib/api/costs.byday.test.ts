import { describe, expect, it } from 'vitest';

import { normalizeCostByDay } from '@/lib/api/costs';

describe('normalizeCostByDay', () => {
  it('maps total_usd and by_provider for AWS/Azure/GCP day rows', () => {
    const day = normalizeCostByDay({
      date: '2026-11-13',
      total_usd: 205,
      by_provider: { aws: 100, azure: 60, gcp: 45 },
      has_estimates: false,
    });
    expect(day.date).toBe('2026-11-13');
    expect(day.total).toBe(205);
    expect(day.by_provider.aws).toBe(100);
    expect(day.by_provider.azure).toBe(60);
    expect(day.by_provider.gcp).toBe(45);
    expect(day.is_estimate).toBe(false);
  });
});
