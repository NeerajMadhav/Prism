/** PRISM FinOps — FinOps scorecard API module. */

import { apiClient } from '@/lib/api/client';
import type { Scorecard, ScorecardExecutive } from '@/types/scorecard';

/** Fetches the FinOps health scorecard. */
export async function get(orgId: string): Promise<Scorecard> {
  const { data } = await apiClient.get<Scorecard>(`/orgs/${orgId}/scorecard`);
  return data;
}

/** Fetches executive summary metrics. */
export async function getExecutive(orgId: string): Promise<ScorecardExecutive> {
  const { data } = await apiClient.get<ScorecardExecutive>(
    `/orgs/${orgId}/scorecard/executive`,
  );
  return data;
}
