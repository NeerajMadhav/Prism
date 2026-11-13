/** PRISM FinOps — outbound webhooks API (normalized pagination). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated } from '@/lib/api/normalize';
import type { Paginated } from '@/types/api';
import type { MessageResponse } from '@/types/auth';
import type {
  CreateWebhookRequest,
  OutboundWebhook,
  UpdateWebhookRequest,
} from '@/types/webhooks';

/** Lists outbound webhooks. */
export async function list(orgId: string): Promise<Paginated<OutboundWebhook>> {
  const { data } = await apiClient.get<OutboundWebhook[] | Paginated<OutboundWebhook>>(
    `/orgs/${orgId}/webhooks`,
  );
  return normalizePaginated(data);
}

/** Creates an outbound webhook. */
export async function create(
  orgId: string,
  body: CreateWebhookRequest,
): Promise<OutboundWebhook> {
  const { data } = await apiClient.post<OutboundWebhook>(
    `/orgs/${orgId}/webhooks`,
    body,
  );
  return data;
}

/** Updates an outbound webhook. */
export async function update(
  orgId: string,
  webhookId: string,
  body: UpdateWebhookRequest,
): Promise<OutboundWebhook> {
  const { data } = await apiClient.put<OutboundWebhook>(
    `/orgs/${orgId}/webhooks/${webhookId}`,
    body,
  );
  return data;
}

/** Deletes an outbound webhook. */
export async function remove(orgId: string, webhookId: string): Promise<void> {
  await apiClient.delete(`/orgs/${orgId}/webhooks/${webhookId}`);
}

/** Sends a test delivery for a webhook. */
export async function test(
  orgId: string,
  webhookId: string,
): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(
    `/orgs/${orgId}/webhooks/${webhookId}/test`,
  );
  return data;
}
