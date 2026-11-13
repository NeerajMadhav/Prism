/** PRISM FinOps — LLM assistant configuration types. */

export type LlmProvider = 'openai' | 'azure_openai';

export interface LlmConfig {
  configured: boolean;
  provider?: LlmProvider;
  model?: string;
  monthly_budget?: number;
  current_spend?: number;
  budget_pct?: number;
}

export interface SetLlmConfigRequest {
  provider: LlmProvider;
  api_key: string;
  model?: string;
  monthly_budget?: number;
}

export interface LlmQueryRequest {
  question: string;
  context_id?: string;
}

export interface LlmQueryResponse {
  answer: string;
  tokens_used: number;
  remaining_queries_this_hour: number;
}
