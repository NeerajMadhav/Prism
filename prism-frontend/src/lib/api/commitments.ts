/** PRISM FinOps — commitments API (normalized pagination). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated, type BackendPaginated } from '@/lib/api/normalize';
import type { Paginated } from '@/types/api';
import type {
  Commitment,
  CommitmentSummary,
} from '@/types/commitments';

/** Lists reserved capacity and savings commitments. */
export async function list(orgId: string): Promise<Paginated<Commitment>> {
  const { data } = await apiClient.get<
    BackendPaginated<Commitment> | Commitment[] | Paginated<Commitment>
  >(`/orgs/${orgId}/commitments`);
  return normalizePaginated(data);
}

/** Fetches aggregate commitment coverage metrics. */
export async function getSummary(orgId: string): Promise<CommitmentSummary> {
  const { data } = await apiClient.get<CommitmentSummary>(
    `/orgs/${orgId}/commitments/summary`,
  );
  return data;
}

/** Lists commitments nearing expiry. */
export async function getExpiring(orgId: string): Promise<Commitment[]> {
  const { data } = await apiClient.get<Commitment[]>(
    `/orgs/${orgId}/commitments/expiring`,
  );
  return Array.isArray(data) ? data : [];
}
