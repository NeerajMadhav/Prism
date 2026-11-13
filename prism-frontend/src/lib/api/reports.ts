/** PRISM FinOps — monthly reports API module. */

import { apiClient } from '@/lib/api/client';
import type {
  ReportConfig,
  SendReportNowResponse,
  UpdateReportConfig,
} from '@/types/reports';

/** Fetches monthly report configuration. */
export async function get(orgId: string): Promise<ReportConfig> {
  const { data } = await apiClient.get<ReportConfig>(`/orgs/${orgId}/reports`);
  return data;
}

/** Updates monthly report configuration. */
export async function update(
  orgId: string,
  body: UpdateReportConfig,
): Promise<ReportConfig> {
  const { data } = await apiClient.put<ReportConfig>(`/orgs/${orgId}/reports`, body);
  return data;
}

/** Queues an immediate report send. */
export async function sendNow(orgId: string): Promise<SendReportNowResponse> {
  const { data } = await apiClient.post<SendReportNowResponse>(
    `/orgs/${orgId}/reports/send-now`,
  );
  return data;
}
