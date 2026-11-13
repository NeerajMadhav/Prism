/** PRISM FinOps — cloud accounts API (normalized to UI types). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated, type BackendPaginated } from '@/lib/api/normalize';
import type { Paginated } from '@/types/api';
import type {
  BackendCloudAccount,
  CloudAccount,
  ConnectRequest,
  ConnectResponse,
  SyncLog,
  SyncResponse,
  TestConnectionResponse,
  UpdateAccountRequest,
} from '@/types/accounts';
import type { SyncStatus } from '@/types/api';

function normalizeStatus(status: string | null | undefined): SyncStatus {
  if (status === 'pending' || status === 'running' || status === 'success' || status === 'failed' || status === 'never') {
    return status;
  }
  if (status === 'completed' || status === 'ok') return 'success';
  if (status === 'error') return 'failed';
  if (!status) return 'never';
  return 'pending';
}

/** Maps backend account rows into UI `CloudAccount`. */
export function normalizeAccount(row: BackendCloudAccount): CloudAccount {
  return {
    id: row.id,
    name: row.display_name,
    provider: row.provider,
    provider_account_id: row.account_id,
    status: row.is_active ? 'active' : 'inactive',
    last_sync_at: row.last_sync,
    last_sync_status: normalizeStatus(row.last_sync_status),
    records_synced: 0,
    data_as_of: row.data_as_of,
    error_message: row.last_sync_error ?? undefined,
    is_active: row.is_active,
    created_at: row.created_at,
  };
}

function normalizeSyncLog(row: Record<string, unknown>, accountId: string): SyncLog {
  return {
    id: String(row.id),
    account_id: accountId,
    started_at: String(row.started_at),
    completed_at: row.finished_at ? String(row.finished_at) : undefined,
    status: normalizeStatus(row.status as string),
    records_synced: typeof row.records_synced === 'number' ? row.records_synced : undefined,
    error_message: row.error ? String(row.error) : undefined,
  };
}

/** Lists connected cloud accounts (backend returns a bare array). */
export async function list(orgId: string): Promise<Paginated<CloudAccount>> {
  const { data } = await apiClient.get<
    BackendPaginated<BackendCloudAccount> | BackendCloudAccount[]
  >(`/orgs/${orgId}/accounts`);
  const page = normalizePaginated(data);
  return {
    ...page,
    items: page.items.map(normalizeAccount),
  };
}

/** Fetches a single cloud account. */
export async function get(orgId: string, accountId: string): Promise<CloudAccount> {
  const { data } = await apiClient.get<BackendCloudAccount>(
    `/orgs/${orgId}/accounts/${accountId}`,
  );
  return normalizeAccount(data);
}

/** Connects a new cloud account. */
export async function connect(
  orgId: string,
  body: ConnectRequest,
): Promise<ConnectResponse> {
  const { data } = await apiClient.post<ConnectResponse>(
    `/orgs/${orgId}/accounts`,
    body,
  );
  return data;
}

/** Updates account metadata. */
export async function update(
  orgId: string,
  accountId: string,
  body: UpdateAccountRequest,
): Promise<CloudAccount> {
  const { data } = await apiClient.put<BackendCloudAccount>(
    `/orgs/${orgId}/accounts/${accountId}`,
    body,
  );
  return normalizeAccount(data);
}

/** Soft-removes a cloud account. */
export async function remove(orgId: string, accountId: string): Promise<void> {
  await apiClient.delete(`/orgs/${orgId}/accounts/${accountId}`);
}

/** Tests account credentials and connectivity. */
export async function test(
  orgId: string,
  accountId: string,
): Promise<TestConnectionResponse> {
  const { data } = await apiClient.post<{ ok: boolean; error?: string | null }>(
    `/orgs/${orgId}/accounts/${accountId}/test`,
  );
  return {
    ok: data.ok,
    message: data.error ? String(data.error) : data.ok ? 'Connection successful' : 'Connection failed',
  };
}

/** Triggers a data sync for an account. */
export async function sync(orgId: string, accountId: string): Promise<SyncResponse> {
  const { data } = await apiClient.post<SyncResponse>(
    `/orgs/${orgId}/accounts/${accountId}/sync`,
  );
  return data;
}

/** Returns sync history for an account. */
export async function getSyncLogs(
  orgId: string,
  accountId: string,
): Promise<Paginated<SyncLog>> {
  const { data } = await apiClient.get<BackendPaginated<Record<string, unknown>>>(
    `/orgs/${orgId}/accounts/${accountId}/sync-logs`,
  );
  const page = normalizePaginated(data);
  return {
    ...page,
    items: page.items.map((row) => normalizeSyncLog(row, accountId)),
  };
}
