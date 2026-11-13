/** PRISM FinOps — alerts API (normalized to UI types). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated, type BackendPaginated } from '@/lib/api/normalize';
import type { Paginated } from '@/types/api';
import type {
  Alert,
  AlertCountResponse,
  AlertListParams,
  AlertStatus,
  BackendAlert,
  SnoozeRequest,
} from '@/types/alerts';

function deriveStatus(row: BackendAlert): AlertStatus {
  if (row.snoozed_until && new Date(row.snoozed_until).getTime() > Date.now()) {
    return 'snoozed';
  }
  if (row.acknowledged_at) {
    return 'acknowledged';
  }
  return 'active';
}

/** Maps backend alert rows into UI `Alert`. */
export function normalizeAlert(row: BackendAlert): Alert {
  return {
    id: row.id,
    type: row.type,
    status: deriveStatus(row),
    scope: row.scope ?? undefined,
    scope_value: row.scope_value ?? undefined,
    severity: row.severity,
    message: row.message,
    cap_id: row.cap_id ?? undefined,
    threshold_pct: row.threshold_percent ?? undefined,
    triggered_at: row.triggered_at,
    snoozed_until: row.snoozed_until,
    acknowledged_at: row.acknowledged_at,
    acknowledged_by: row.acknowledged_by ?? undefined,
  };
}

/** Lists alerts with optional filters mapped to backend query params. */
export async function list(
  orgId: string,
  params?: AlertListParams,
): Promise<Paginated<Alert>> {
  const query: Record<string, string | number | boolean> = {};
  if (params?.page) query.page = params.page;
  if (params?.size) query.limit = params.size;
  if (params?.type) query.type = params.type;
  if (params?.acknowledged !== undefined) {
    query.acknowledged = params.acknowledged ? 'true' : 'false';
  } else if (params?.status === 'active') {
    query.acknowledged = 'false';
  }

  const { data } = await apiClient.get<BackendPaginated<BackendAlert>>(
    `/orgs/${orgId}/alerts`,
    { params: query },
  );
  const page = normalizePaginated(data);
  let items = page.items.map(normalizeAlert);
  if (params?.status === 'acknowledged') {
    items = items.filter((a) => a.status === 'acknowledged');
  } else if (params?.status === 'snoozed') {
    items = items.filter((a) => a.status === 'snoozed');
  } else if (params?.status === 'active') {
    items = items.filter((a) => a.status === 'active');
  }
  return { ...page, items, total: params?.status ? items.length : page.total };
}

/** Acknowledges an alert. */
export async function acknowledge(orgId: string, alertId: string): Promise<Alert> {
  const { data } = await apiClient.post<BackendAlert>(
    `/orgs/${orgId}/alerts/${alertId}/acknowledge`,
  );
  return normalizeAlert(data);
}

/** Snoozes an alert until a datetime (backend field: snooze_until). */
export async function snooze(
  orgId: string,
  alertId: string,
  body: SnoozeRequest,
): Promise<Alert> {
  const { data } = await apiClient.post<BackendAlert>(
    `/orgs/${orgId}/alerts/${alertId}/snooze`,
    { snooze_until: body.until },
  );
  return normalizeAlert(data);
}

/**
 * Returns active alert count.
 * Prefer dedicated `/count` when present; otherwise derive from list total.
 */
export async function count(orgId: string): Promise<AlertCountResponse> {
  try {
    const { data } = await apiClient.get<AlertCountResponse>(
      `/orgs/${orgId}/alerts/count`,
    );
    if (typeof data?.active === 'number') {
      return data;
    }
  } catch {
    // Endpoint may be missing on current backend — fall through.
  }
  const page = await list(orgId, { status: 'active', page: 1, size: 1 });
  return { active: page.total };
}
