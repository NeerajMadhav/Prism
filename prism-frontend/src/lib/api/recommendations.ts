/** PRISM FinOps — recommendations API (normalized to UI types). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated, type BackendPaginated } from '@/lib/api/normalize';
import type { Paginated, Provider } from '@/types/api';
import type {
  RecConfidence,
  RecStatus,
  Recommendation,
  RecommendationListParams,
} from '@/types/recommendations';

interface BackendRecommendation {
  id: string;
  type: string;
  title: string;
  description?: string | null;
  savings_usd?: number;
  confidence?: string | null;
  status: string;
  created_at: string;
  metadata?: { provider?: string; region?: string; service?: string };
  provider?: string;
  service?: string;
  region?: string;
}

function asConfidence(value: string | null | undefined): RecConfidence {
  if (value === 'high' || value === 'medium' || value === 'low') return value;
  return 'medium';
}

function asStatus(value: string): RecStatus {
  if (
    value === 'open' ||
    value === 'implemented' ||
    value === 'rejected' ||
    value === 'archived'
  ) {
    return value;
  }
  return 'open';
}

/** Maps backend recommendation rows into UI `Recommendation`. */
export function normalizeRecommendation(row: BackendRecommendation): Recommendation {
  const meta = row.metadata ?? {};
  const provider = (row.provider ?? meta.provider ?? 'aws') as Provider;
  return {
    id: row.id,
    title: row.title,
    description: row.description ?? '',
    provider,
    region: row.region ?? meta.region,
    service: row.service ?? meta.service ?? row.type,
    type: row.type,
    estimated_savings_monthly: row.savings_usd ?? 0,
    confidence: asConfidence(row.confidence),
    status: asStatus(row.status),
    created_at: row.created_at,
  };
}

/** Lists optimization recommendations. */
export async function list(
  orgId: string,
  params?: RecommendationListParams,
): Promise<Paginated<Recommendation>> {
  const query: Record<string, string | number> = {};
  if (params?.status) query.status = params.status;
  if (params?.provider) query.provider = params.provider;
  if (params?.confidence) query.confidence = params.confidence;
  if (params?.min_savings !== undefined) query.min_savings = params.min_savings;

  const { data } = await apiClient.get<
    BackendPaginated<BackendRecommendation> | BackendRecommendation[]
  >(`/orgs/${orgId}/recommendations`, { params: query });
  const page = normalizePaginated(data);
  return { ...page, items: page.items.map(normalizeRecommendation) };
}

/** Updates recommendation workflow status. */
export async function updateStatus(
  orgId: string,
  recId: string,
  status: RecStatus,
): Promise<Recommendation> {
  const { data } = await apiClient.put<BackendRecommendation>(
    `/orgs/${orgId}/recommendations/${recId}/status`,
    { status },
  );
  return normalizeRecommendation({
    ...data,
    description: data.description ?? '',
    created_at: data.created_at ?? new Date().toISOString(),
    type: data.type ?? 'unknown',
  });
}
