/** PRISM FinOps — virtual tag rules API (normalized pagination). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated } from '@/lib/api/normalize';
import type { Paginated } from '@/types/api';
import type {
  CreateVirtualTagRuleRequest,
  ReorderVirtualTagRulesRequest,
  UpdateVirtualTagRuleRequest,
  VirtualTagAudit,
  VirtualTagRule,
} from '@/types/virtual-tags';

/** Lists virtual tag rules in priority order. */
export async function list(orgId: string): Promise<Paginated<VirtualTagRule>> {
  const { data } = await apiClient.get<VirtualTagRule[] | Paginated<VirtualTagRule>>(
    `/orgs/${orgId}/virtual-tags`,
  );
  return normalizePaginated(data);
}

/** Creates a virtual tag rule. */
export async function create(
  orgId: string,
  body: CreateVirtualTagRuleRequest,
): Promise<VirtualTagRule> {
  const { data } = await apiClient.post<VirtualTagRule>(
    `/orgs/${orgId}/virtual-tags`,
    body,
  );
  return data;
}

/** Updates a virtual tag rule. */
export async function update(
  orgId: string,
  ruleId: string,
  body: UpdateVirtualTagRuleRequest,
): Promise<VirtualTagRule> {
  const { data } = await apiClient.put<VirtualTagRule>(
    `/orgs/${orgId}/virtual-tags/${ruleId}`,
    body,
  );
  return data;
}

/** Deletes a virtual tag rule. */
export async function remove(orgId: string, ruleId: string): Promise<void> {
  await apiClient.delete(`/orgs/${orgId}/virtual-tags/${ruleId}`);
}

/** Reorders rules by explicit ID list. */
export async function reorder(
  orgId: string,
  body: ReorderVirtualTagRulesRequest,
): Promise<VirtualTagRule[]> {
  const { data } = await apiClient.put<VirtualTagRule[]>(
    `/orgs/${orgId}/virtual-tags/reorder`,
    body,
  );
  return Array.isArray(data) ? data : [];
}

/** Applies a rule to historical cost rows. */
export async function apply(
  orgId: string,
  ruleId: string,
): Promise<VirtualTagAudit> {
  const { data } = await apiClient.post<VirtualTagAudit>(
    `/orgs/${orgId}/virtual-tags/${ruleId}/apply`,
  );
  return data;
}

/** Returns virtual tag apply audit history. */
export async function getAuditLog(
  orgId: string,
): Promise<Paginated<VirtualTagAudit>> {
  const { data } = await apiClient.get<VirtualTagAudit[] | Paginated<VirtualTagAudit>>(
    `/orgs/${orgId}/virtual-tags/audit-log`,
  );
  return normalizePaginated(data);
}
