/** PRISM FinOps — cloud account and sync types (aligned to live backend). */

import type { Provider, SyncStatus } from '@/types/api';

export type { Provider, SyncStatus };

/** Normalized account used by UI components. */
export interface CloudAccount {
  id: string;
  name: string;
  provider: Provider;
  provider_account_id: string;
  status: string;
  last_sync_at: string | null;
  last_sync_status: SyncStatus;
  records_synced: number;
  data_as_of: string | null;
  error_message?: string;
  is_active: boolean;
  created_at: string;
}

/** Raw account payload from FastAPI. */
export interface BackendCloudAccount {
  id: string;
  provider: Provider;
  account_id: string;
  display_name: string;
  scope?: string;
  last_sync: string | null;
  last_sync_status: SyncStatus | string | null;
  last_sync_error?: string | null;
  data_as_of: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SyncLog {
  id: string;
  account_id: string;
  started_at: string;
  completed_at?: string;
  status: SyncStatus;
  records_synced?: number;
  error_message?: string;
  duration_ms?: number;
}

export interface AwsConnectRequest {
  provider: 'aws';
  display_name: string;
  credentials: {
    role_arn: string;
    external_id: string;
    region: string;
  };
  scope?: string;
}

export interface AzureConnectRequest {
  provider: 'azure';
  display_name: string;
  credentials: {
    tenant_id: string;
    client_id: string;
    client_secret: string;
    subscription_id: string;
  };
  scope?: string;
}

export interface GcpConnectRequest {
  provider: 'gcp';
  display_name: string;
  credentials: {
    project_id: string;
    dataset_id: string;
    table_prefix: string;
    service_account_json: Record<string, unknown>;
  };
  scope?: string;
}

export type ConnectRequest = AwsConnectRequest | AzureConnectRequest | GcpConnectRequest;

export interface ConnectResponse {
  id: string;
  provider: Provider;
  account_id: string;
  display_name: string;
  sync_task_id?: string;
  sync_mode?: 'queued' | 'inline';
}

export interface TestConnectionResponse {
  ok: boolean;
  message: string;
  latency_ms?: number;
}

export interface UpdateAccountRequest {
  display_name?: string;
}

export interface SyncResponse {
  sync_task_id?: string;
  task_id?: string;
  sync_mode?: 'queued' | 'inline';
  message?: string;
}
