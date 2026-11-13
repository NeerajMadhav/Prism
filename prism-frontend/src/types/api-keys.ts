/** PRISM FinOps — API key types. */

export type ApiKeyScope =
  | 'cost.read'
  | 'alerts.read'
  | 'reports.read'
  | 'webhooks.write';

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  scopes: ApiKeyScope[];
  created_at: string;
  last_used_at?: string;
}

export interface CreateApiKeyRequest {
  name: string;
  scopes: ApiKeyScope[];
}

export interface CreateApiKeyResponse {
  key: ApiKey;
  raw_key: string;
}
