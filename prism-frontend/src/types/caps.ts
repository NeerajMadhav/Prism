/** PRISM FinOps — budget cap types. */

import type { Provider } from '@/types/api';

export type CapScope = 'platform' | 'service' | 'account';

export interface BudgetCap {
  id: string;
  name: string;
  provider?: Provider;
  scope: CapScope;
  service?: string;
  account_id?: string;
  amount: number;
  currency: string;
  period: string;
  thresholds: number[];
  current_spend: number;
  pct_used: number;
  next_threshold: number | null;
  last_alert_at?: string;
  created_at: string;
}

export interface CreateCapRequest {
  name: string;
  provider?: Provider;
  scope: CapScope;
  service?: string;
  account_id?: string;
  amount: number;
  thresholds: number[];
}

export type UpdateCapRequest = Partial<CreateCapRequest>;
