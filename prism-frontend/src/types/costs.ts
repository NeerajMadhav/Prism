/** PRISM FinOps — cost analytics types. */

import type { Provider } from '@/types/api';

export type CostView = 'unblended' | 'amortized';

export interface CostQueryParams {
  start?: string;
  end?: string;
  provider?: Provider;
  view?: CostView;
  account_id?: string;
}

export interface CostSummary {
  total: number;
  mom_pct: number | null;
  mom_abs: number | null;
  is_estimate: boolean;
  data_as_of: string | null;
  currency: string;
  provider?: Provider;
}

export interface CostByDay {
  date: string;
  total: number;
  by_provider: Record<Provider, number>;
  is_estimate: boolean;
}

export interface CostByService {
  service: string;
  provider: Provider;
  total: number;
  mom_pct: number | null;
  mom_abs: number | null;
  trend: number[];
}

export interface CostByTag {
  tag_key: string;
  tag_value: string;
  total: number;
  pct_of_total: number;
}

export interface TopService {
  service: string;
  provider: Provider;
  total: number;
  mom_pct: number | null;
  rank: number;
}
