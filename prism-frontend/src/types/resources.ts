/** PRISM FinOps — cloud resource inventory types. */

import type { Provider } from '@/types/api';

export interface Resource {
  id: string;
  name: string;
  type: string;
  provider: Provider;
  region: string;
  account_id: string;
  is_idle: boolean;
  idle_since?: string;
  last_active_at?: string;
  cost_per_day: number;
  tags: Record<string, string>;
  discovered_at: string;
}

export interface ResourceListParams {
  provider?: Provider;
  region?: string;
  type?: string;
  page?: number;
  size?: number;
}
