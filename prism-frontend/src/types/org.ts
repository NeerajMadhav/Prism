/** PRISM FinOps — organization types. */

export interface OrgDetail {
  id: string;
  name: string;
  plan: string;
  billing_period_start: string | null;
  currency: string;
  timezone: string;
  feature_flags: Record<string, unknown>;
  created_at: string;
}

export interface UpdateOrgRequest {
  name?: string;
  timezone?: string;
  currency?: string;
  billing_period_start?: string | null;
}
