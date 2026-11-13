/** PRISM FinOps — resource inventory API (normalized to UI types). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated, type BackendPaginated } from '@/lib/api/normalize';
import type { Paginated, Provider } from '@/types/api';
import type { Resource, ResourceListParams } from '@/types/resources';

interface BackendResource {
  id: string;
  provider: Provider;
  resource_id?: string;
  resource_type?: string;
  name?: string | null;
  region?: string | null;
  account_id?: string | null;
  tags?: Record<string, string> | null;
  last_cost_usd?: number | null;
  is_idle?: boolean;
  idle_since?: string | null;
  last_seen?: string | null;
}

/** Maps backend resource rows into UI `Resource`. */
export function normalizeResource(row: BackendResource): Resource {
  return {
    id: row.id,
    name: row.name ?? row.resource_id ?? row.id,
    type: row.resource_type ?? 'unknown',
    provider: row.provider,
    region: row.region ?? '',
    account_id: row.account_id ?? '',
    is_idle: Boolean(row.is_idle),
    idle_since: row.idle_since ?? undefined,
    last_active_at: row.last_seen ?? undefined,
    cost_per_day: row.last_cost_usd ?? 0,
    tags: row.tags ?? {},
    discovered_at: row.last_seen ?? new Date(0).toISOString(),
  };
}

/** Lists cloud resources with optional filters. */
export async function list(
  orgId: string,
  params?: ResourceListParams,
): Promise<Paginated<Resource>> {
  const query: Record<string, string | number> = {};
  if (params?.page) query.page = params.page;
  if (params?.size) query.limit = params.size;
  if (params?.provider) query.provider = params.provider;
  if (params?.region) query.region = params.region;
  if (params?.type) query.type = params.type;

  const { data } = await apiClient.get<
    BackendPaginated<BackendResource> | BackendResource[]
  >(`/orgs/${orgId}/resources`, { params: query });
  const page = normalizePaginated(data);
  return { ...page, items: page.items.map(normalizeResource) };
}

/** Lists idle resources (backend returns a bare array). */
export async function listIdle(orgId: string): Promise<Paginated<Resource>> {
  const { data } = await apiClient.get<BackendResource[]>(
    `/orgs/${orgId}/resources/idle`,
  );
  const page = normalizePaginated(data);
  return { ...page, items: page.items.map(normalizeResource) };
}

/** Fetches a single resource. */
export async function get(orgId: string, resourceId: string): Promise<Resource> {
  const { data } = await apiClient.get<BackendResource>(
    `/orgs/${orgId}/resources/${resourceId}`,
  );
  return normalizeResource(data);
}
