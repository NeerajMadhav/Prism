/** PRISM FinOps — optimization recommendation types. */

import type { Provider } from '@/types/api';

export type RecStatus = 'open' | 'implemented' | 'rejected' | 'archived';

export type RecConfidence = 'high' | 'medium' | 'low';

export interface Recommendation {
  id: string;
  title: string;
  description: string;
  provider: Provider;
  region?: string;
  service: string;
  type: string;
  estimated_savings_monthly: number;
  confidence: RecConfidence;
  status: RecStatus;
  created_at: string;
  resolved_at?: string;
}

export interface RecommendationListParams {
  status?: RecStatus;
  provider?: Provider;
  min_savings?: number;
  confidence?: RecConfidence;
}
