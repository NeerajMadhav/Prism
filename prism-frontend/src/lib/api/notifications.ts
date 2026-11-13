/** PRISM FinOps — notification settings API module. */

import { apiClient } from '@/lib/api/client';
import type { MessageResponse } from '@/types/auth';
import type {
  NotificationSettings,
  UpdateNotificationSettings,
} from '@/types/notifications';

/** Fetches notification channel settings. */
export async function get(orgId: string): Promise<NotificationSettings> {
  const { data } = await apiClient.get<NotificationSettings>(
    `/orgs/${orgId}/notifications`,
  );
  return data;
}

/** Updates notification channel settings. */
export async function update(
  orgId: string,
  body: UpdateNotificationSettings,
): Promise<NotificationSettings> {
  const { data } = await apiClient.put<NotificationSettings>(
    `/orgs/${orgId}/notifications`,
    body,
  );
  return data;
}

/** Sends a test email notification. */
export async function testEmail(orgId: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(
    `/orgs/${orgId}/notifications/test-email`,
  );
  return data;
}

/** Sends a test Microsoft Teams notification. */
export async function testTeams(orgId: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(
    `/orgs/${orgId}/notifications/test-teams`,
  );
  return data;
}

/** Sends a test Slack notification. */
export async function testSlack(orgId: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(
    `/orgs/${orgId}/notifications/test-slack`,
  );
  return data;
}
