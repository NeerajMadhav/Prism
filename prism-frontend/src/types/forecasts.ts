/** PRISM FinOps — spend forecast types. */

import type { Provider } from '@/types/api';

export interface Forecast {
  provider: Provider;
  projected_total: number;
  cap_amount?: number;
  pct_of_cap?: number;
  days_elapsed: number;
  days_in_month: number;
  daily_avg: number;
  will_breach: boolean;
  currency: string;
  computed_at: string;
}

export interface ForecastHistory {
  month: string;
  provider: Provider;
  projected: number;
  actual?: number;
  variance_pct?: number;
  accuracy_pct?: number;
  cap_amount?: number;
}
