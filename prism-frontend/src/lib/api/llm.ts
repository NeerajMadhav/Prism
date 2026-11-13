/** PRISM FinOps — LLM assistant API module. */

import { apiClient } from '@/lib/api/client';
import type { MessageResponse } from '@/types/auth';
import type {
  LlmConfig,
  LlmQueryRequest,
  LlmQueryResponse,
  SetLlmConfigRequest,
} from '@/types/llm';

/** Fetches LLM integration configuration. */
export async function getConfig(orgId: string): Promise<LlmConfig> {
  const { data } = await apiClient.get<LlmConfig>(`/orgs/${orgId}/llm`);
  return data;
}

/** Sets or updates LLM provider configuration. */
export async function setConfig(
  orgId: string,
  body: SetLlmConfigRequest,
): Promise<LlmConfig> {
  const { data } = await apiClient.put<LlmConfig>(`/orgs/${orgId}/llm`, body);
  return data;
}

/** Removes LLM configuration. */
export async function deleteConfig(orgId: string): Promise<MessageResponse> {
  const { data } = await apiClient.delete<MessageResponse>(`/orgs/${orgId}/llm`);
  return data;
}

/** Submits a natural-language FinOps query. */
export async function query(
  orgId: string,
  body: LlmQueryRequest,
): Promise<LlmQueryResponse> {
  const { data } = await apiClient.post<LlmQueryResponse>(
    `/orgs/${orgId}/llm/query`,
    body,
  );
  return data;
}
