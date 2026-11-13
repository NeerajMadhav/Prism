/** PRISM FinOps — cost analytics API (normalized to UI types). */

import { apiClient } from '@/lib/api/client';
import { computeMomPct } from '@/lib/api/normalize';
import type { Provider } from '@/types/api';
import type {
  CostByDay,
  CostByService,
  CostByTag,
  CostQueryParams,
  CostSummary,
  TopService,
} from '@/types/costs';

interface BackendCostSummary {
  total_usd: number;
  total_amortized_usd?: number;
  prev_month_total_usd?: number;
  data_as_of?: string | null;
  view?: string;
  month?: string;
  by_provider?: Array<{ provider: string; total_usd: number }>;
}

interface BackendTopService {
  service: string;
  provider: Provider;
  total_usd: number;
  rank: number;
}

interface BackendByDay {
  date?: string;
  day?: string;
  total_usd?: number;
  total?: number;
  by_provider?: Record<string, number>;
  is_estimate?: boolean;
  has_estimates?: boolean;
  has_data?: boolean;
}

interface BackendByDayEnvelope {
  days?: BackendByDay[];
  data?: BackendByDay[];
  providers?: string[];
  month?: string;
  timezone?: string;
  billing_day_basis?: string;
  data_as_of?: string | null;
}

/** Fetches cost summary KPIs. */
export async function getSummary(
  orgId: string,
  params?: CostQueryParams,
): Promise<CostSummary> {
  const { data } = await apiClient.get<BackendCostSummary>(`/orgs/${orgId}/costs`, {
    params: {
      view: params?.view,
      // Backend currently keys off `month` (YYYY-MM); map start→month when provided.
      month: params?.start?.slice(0, 7),
    },
  });
  const total = data.total_usd ?? 0;
  const prev = data.prev_month_total_usd ?? 0;
  return {
    total,
    mom_pct: computeMomPct(total, prev),
    mom_abs: total - prev,
    is_estimate: false,
    data_as_of: data.data_as_of ?? null,
    currency: 'USD',
  };
}

/** Maps one backend day row into UI `CostByDay` (UTC calendar day, per provider). */
export function normalizeCostByDay(row: BackendByDay): CostByDay {
  const byProvider = { ...(row.by_provider ?? {}) } as Record<Provider, number>;
  return {
    date: String(row.date ?? row.day ?? ''),
    total: Number(row.total_usd ?? row.total ?? 0),
    by_provider: byProvider,
    is_estimate: Boolean(row.is_estimate ?? row.has_estimates),
  };
}

/** Fetches daily cost breakdown (UTC day buckets; AWS/Azure/GCP columns). */
export async function getByDay(
  orgId: string,
  params?: CostQueryParams,
): Promise<CostByDay[]> {
  const { data } = await apiClient.get<BackendByDay[] | BackendByDayEnvelope>(
    `/orgs/${orgId}/costs/by-day`,
    {
      params: {
        view: params?.view,
        month: params?.start?.slice(0, 7),
        provider: params?.provider,
      },
    },
  );
  // Live FastAPI shape: `{ days: [...], providers, timezone: "UTC", ... }`
  const rows = Array.isArray(data)
    ? data
    : (data.days ?? data.data ?? []);
  return rows.map(normalizeCostByDay);
}

/** Fetches costs grouped by service. */
export async function getByService(
  orgId: string,
  params?: CostQueryParams,
): Promise<CostByService[]> {
  const { data } = await apiClient.get<
    Array<{ service: string; provider: Provider; total_usd: number }> | { data: Array<{ service: string; provider: Provider; total_usd: number }> }
  >(`/orgs/${orgId}/costs/by-service`, {
    params: {
      view: params?.view,
      month: params?.start?.slice(0, 7),
    },
  });
  const rows = Array.isArray(data) ? data : data.data;
  return (rows ?? []).map((row) => ({
    service: row.service,
    provider: row.provider,
    total: row.total_usd,
    mom_pct: null,
    mom_abs: null,
    trend: [],
  }));
}

/** Fetches costs grouped by tag. */
export async function getByTag(
  orgId: string,
  tagKey: string,
  params?: CostQueryParams,
): Promise<CostByTag[]> {
  const { data } = await apiClient.get<
    Array<{ tag_key?: string; tag_value: string; total_usd: number; pct?: number }> | { data: Array<{ tag_value: string; total_usd: number; pct?: number }> }
  >(`/orgs/${orgId}/costs/by-tag`, {
    params: {
      tag_key: tagKey,
      view: params?.view,
      month: params?.start?.slice(0, 7),
    },
  });
  const rows = Array.isArray(data) ? data : data.data;
  return (rows ?? []).map((row) => ({
    tag_key: tagKey,
    tag_value: row.tag_value,
    total: row.total_usd,
    pct_of_total: row.pct ?? 0,
  }));
}

/** Fetches top services by spend. */
export async function getTopServices(
  orgId: string,
  params?: CostQueryParams,
): Promise<TopService[]> {
  const { data } = await apiClient.get<BackendTopService[]>(
    `/orgs/${orgId}/costs/top-services`,
    {
      params: {
        view: params?.view,
        month: params?.start?.slice(0, 7),
      },
    },
  );
  return (data ?? []).map((row) => ({
    service: row.service,
    provider: row.provider,
    total: row.total_usd,
    mom_pct: null,
    rank: row.rank,
  }));
}
