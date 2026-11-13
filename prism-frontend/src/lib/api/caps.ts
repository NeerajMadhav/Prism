/** PRISM FinOps — budget caps API (normalized to UI types). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated } from '@/lib/api/normalize';
import type { Paginated, Provider } from '@/types/api';
import type {
  BudgetCap,
  CreateCapRequest,
  UpdateCapRequest,
} from '@/types/caps';

interface BackendCap {
  id: string;
  name: string;
  scope: 'platform' | 'service' | 'account';
  scope_value: string;
  cap_amount: number;
  period: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  current_month_spend?: number | null;
  pct_used?: number | null;
}

function scopeFields(cap: BackendCap): Pick<BudgetCap, 'provider' | 'service' | 'account_id'> {
  if (cap.scope === 'platform') {
    return { provider: cap.scope_value as Provider };
  }
  if (cap.scope === 'service') {
    return { service: cap.scope_value };
  }
  return { account_id: cap.scope_value };
}

/** Maps backend cap rows into UI `BudgetCap`. */
export function normalizeCap(row: BackendCap): BudgetCap {
  const spend = row.current_month_spend ?? 0;
  const pct = row.pct_used ?? 0;
  return {
    id: row.id,
    name: row.name,
    scope: row.scope,
    ...scopeFields(row),
    amount: row.cap_amount,
    currency: 'USD',
    period: row.period,
    thresholds: [50, 80, 100],
    current_spend: spend,
    pct_used: pct,
    next_threshold: pct >= 100 ? null : pct >= 80 ? 100 : pct >= 50 ? 80 : 50,
    created_at: row.created_at,
  };
}

function toBackendCreate(body: CreateCapRequest): {
  name: string;
  scope: CreateCapRequest['scope'];
  scope_value: string;
  cap_amount: number;
  period: string;
} {
  const scope_value =
    body.scope === 'platform'
      ? body.provider ?? ''
      : body.scope === 'service'
        ? body.service ?? ''
        : body.account_id ?? '';
  if (!scope_value) {
    throw new Error(`Missing scope_value for cap scope "${body.scope}"`);
  }
  return {
    name: body.name,
    scope: body.scope,
    scope_value,
    cap_amount: body.amount,
    period: 'monthly',
  };
}

/** Lists budget caps. */
export async function list(orgId: string): Promise<Paginated<BudgetCap>> {
  const { data } = await apiClient.get<BackendCap[] | Paginated<BackendCap>>(
    `/orgs/${orgId}/caps`,
  );
  const page = normalizePaginated(data);
  return { ...page, items: page.items.map(normalizeCap) };
}

/** Fetches a single budget cap. */
export async function get(orgId: string, capId: string): Promise<BudgetCap> {
  const { data } = await apiClient.get<BackendCap>(`/orgs/${orgId}/caps/${capId}`);
  return normalizeCap(data);
}

/** Creates a budget cap. */
export async function create(
  orgId: string,
  body: CreateCapRequest,
): Promise<BudgetCap> {
  const { data } = await apiClient.post<BackendCap>(
    `/orgs/${orgId}/caps`,
    toBackendCreate(body),
  );
  return normalizeCap(data);
}

/** Updates a budget cap. */
export async function update(
  orgId: string,
  capId: string,
  body: UpdateCapRequest,
): Promise<BudgetCap> {
  const payload: Record<string, unknown> = {};
  if (body.name !== undefined) payload.name = body.name;
  if (body.amount !== undefined) payload.cap_amount = body.amount;
  const { data } = await apiClient.put<BackendCap>(
    `/orgs/${orgId}/caps/${capId}`,
    payload,
  );
  return normalizeCap(data);
}

/** Deletes a budget cap. */
export async function remove(orgId: string, capId: string): Promise<void> {
  await apiClient.delete(`/orgs/${orgId}/caps/${capId}`);
}
