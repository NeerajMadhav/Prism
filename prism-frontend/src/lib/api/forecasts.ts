/** PRISM FinOps — spend forecasts API (normalized to UI types). */

import { apiClient } from '@/lib/api/client';
import type { Provider } from '@/types/api';
import type { Forecast, ForecastHistory } from '@/types/forecasts';

interface BackendForecast {
  month?: string;
  provider: Provider;
  daily_avg?: number | null;
  projected_total?: number | null;
  cap_amount?: number | null;
  will_breach?: boolean | null;
  days_elapsed?: number | null;
  days_with_data?: number | null;
  data_coverage?: string | null;
  computed_at?: string | null;
}

interface BackendForecastHistory {
  month: string;
  provider: Provider;
  projected_total?: number | null;
  actual_total?: number | null;
  variance_pct?: number | null;
  cap_amount?: number | null;
}

function daysInMonthFromComputed(computedAt?: string | null, month?: string): number {
  if (month && /^\d{4}-\d{2}$/.test(month)) {
    const [y, m] = month.split('-').map(Number);
    return new Date(Date.UTC(y, m, 0)).getUTCDate();
  }
  if (computedAt) {
    const d = new Date(computedAt);
    return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
  }
  return 30;
}

/** Maps backend forecast rows into UI `Forecast`. */
export function normalizeForecast(row: BackendForecast): Forecast {
  const projected = row.projected_total ?? 0;
  const cap = row.cap_amount ?? undefined;
  return {
    provider: row.provider,
    projected_total: projected,
    cap_amount: cap,
    pct_of_cap: cap ? (projected / cap) * 100 : undefined,
    days_elapsed: row.days_elapsed ?? 0,
    days_in_month: daysInMonthFromComputed(row.computed_at, row.month),
    daily_avg: row.daily_avg ?? 0,
    will_breach: Boolean(row.will_breach),
    currency: 'USD',
    computed_at: row.computed_at ?? new Date().toISOString(),
  };
}

/** Fetches current-month forecasts. */
export async function getCurrent(orgId: string): Promise<Forecast[]> {
  const { data } = await apiClient.get<BackendForecast[] | BackendForecast>(
    `/orgs/${orgId}/forecasts`,
  );
  const rows = Array.isArray(data) ? data : data ? [data] : [];
  return rows
    .filter((row) => row.projected_total != null || row.data_coverage !== 'insufficient')
    .map(normalizeForecast);
}

/** Fetches historical forecast accuracy. */
export async function getHistory(orgId: string): Promise<ForecastHistory[]> {
  const { data } = await apiClient.get<BackendForecastHistory[]>(
    `/orgs/${orgId}/forecasts/history`,
  );
  const rows = Array.isArray(data) ? data : [];
  return rows.map((row) => ({
    month: row.month,
    provider: row.provider,
    projected: row.projected_total ?? 0,
    actual: row.actual_total ?? undefined,
    variance_pct: row.variance_pct ?? undefined,
    cap_amount: row.cap_amount ?? undefined,
  }));
}
