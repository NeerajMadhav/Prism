import { describe, expect, it } from 'vitest';

import { normalizeForecast } from '@/lib/api/forecasts';

describe('normalizeForecast', () => {
  it('coerces null projected_total and computes pct_of_cap', () => {
    const forecast = normalizeForecast({
      month: '2026-11',
      provider: 'aws',
      projected_total: null,
      cap_amount: 10000,
      daily_avg: 100,
      days_elapsed: 13,
      will_breach: false,
      computed_at: '2026-11-13T00:00:00+00:00',
    });
    expect(forecast.projected_total).toBe(0);
    expect(forecast.pct_of_cap).toBe(0);
    expect(forecast.days_in_month).toBe(30);
    expect(forecast.currency).toBe('USD');
  });
});
