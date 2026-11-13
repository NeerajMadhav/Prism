/** PRISM FinOps — organization API module. */

import { apiClient } from '@/lib/api/client';
import type { OrgDetail, UpdateOrgRequest } from '@/types/org';

/** Fetches organization details. */
export async function getOrg(orgId: string): Promise<OrgDetail> {
  const { data } = await apiClient.get<OrgDetail>(`/orgs/${orgId}`);
  return data;
}

/** Updates organization settings. */
export async function updateOrg(
  orgId: string,
  body: UpdateOrgRequest,
): Promise<OrgDetail> {
  const { data } = await apiClient.put<OrgDetail>(`/orgs/${orgId}`, body);
  return data;
}
