/** PRISM FinOps — commitment and coverage types. */

import type { Provider } from '@/types/api';

export type CommitmentType = 'reserved_instance' | 'savings_plan' | 'cud';

export type CommitmentStatus = 'active' | 'expiring' | 'expired';

export interface Commitment {
  id: string;
  provider: Provider;
  type: CommitmentType;
  resource_type: string;
  coverage_pct: number;
  utilization_pct: number;
  start_date: string;
  end_date: string;
  days_to_expiry: number;
  status: CommitmentStatus;
  monthly_cost: number;
}

export interface CommitmentSummary {
  coverage_pct: number;
  utilization_pct: number;
  expiring_count: number;
  total_monthly_cost: number;
}
