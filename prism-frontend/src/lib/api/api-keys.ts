/** PRISM FinOps — API keys API (normalized pagination). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated } from '@/lib/api/normalize';
import type { Paginated } from '@/types/api';
import type {
  ApiKey,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
} from '@/types/api-keys';

/** Lists organization API keys. */
export async function list(orgId: string): Promise<Paginated<ApiKey>> {
  const { data } = await apiClient.get<ApiKey[] | Paginated<ApiKey>>(
    `/orgs/${orgId}/api-keys`,
  );
  return normalizePaginated(data);
}

/** Creates a new API key (raw key returned once). */
export async function create(
  orgId: string,
  body: CreateApiKeyRequest,
): Promise<CreateApiKeyResponse> {
  const { data } = await apiClient.post<CreateApiKeyResponse>(
    `/orgs/${orgId}/api-keys`,
    body,
  );
  return data;
}

/** Revokes an API key. */
export async function revoke(orgId: string, keyId: string): Promise<void> {
  await apiClient.delete(`/orgs/${orgId}/api-keys/${keyId}`);
}
