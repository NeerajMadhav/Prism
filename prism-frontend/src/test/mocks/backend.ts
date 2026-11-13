/** Realistic mock payloads matching live FastAPI response shapes. */

import type { BackendCloudAccount } from '@/types/accounts';
import type { BackendAlert } from '@/types/alerts';

export const MOCK_ORG_ID = '11111111-1111-1111-1111-111111111111';
export const MOCK_USER_ID = '22222222-2222-2222-2222-222222222222';

export const mockBackendAccount: BackendCloudAccount = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  provider: 'aws',
  account_id: '123456789012',
  display_name: 'Prod AWS',
  scope: 'organization',
  last_sync: '2026-11-13T10:00:00+00:00',
  last_sync_status: 'success',
  last_sync_error: null,
  data_as_of: '2026-11-12',
  is_active: true,
  created_at: '2026-11-01T00:00:00+00:00',
};

export const mockBackendAlert: BackendAlert = {
  id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  type: 'cap_threshold',
  scope: 'platform',
  scope_value: null,
  severity: 'warning',
  threshold_percent: 90,
  message: 'AWS spend crossed 90% of cap',
  triggered_at: '2026-11-13T08:00:00+00:00',
  acknowledged_at: null,
  acknowledged_by: null,
  snoozed_until: null,
  cap_id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
};

export const mockCostSummary = {
  month: '2026-11',
  view: 'unblended',
  total_usd: 12453.2,
  total_amortized_usd: 12000,
  prev_month_total_usd: 11000,
  data_as_of: '2026-11-12',
  by_provider: [{ provider: 'aws', total_usd: 12453.2 }],
};

export const mockTopServices = [
  { service: 'AmazonEC2', provider: 'aws' as const, total_usd: 4200, rank: 1 },
  { service: 'AmazonS3', provider: 'aws' as const, total_usd: 1100, rank: 2 },
];

export const mockLoginResponse = {
  access_token: 'access.jwt.token',
  refresh_token: 'refresh.opaque.token',
  user: {
    id: MOCK_USER_ID,
    email: 'finops@example.com',
    name: 'FinOps User',
    org_id: MOCK_ORG_ID,
    role: 'owner' as const,
  },
};

export const mockMeFlat = {
  id: MOCK_USER_ID,
  email: 'finops@example.com',
  name: 'FinOps User',
  avatar_url: null,
  org_id: MOCK_ORG_ID,
  org_name: 'Acme Cloud',
  role: 'owner',
  email_verified: true,
  last_login: '2026-11-13T09:00:00+00:00',
};

export function mockPaginated<T>(items: T[], page = 1, limit = 20) {
  return {
    data: items,
    pagination: {
      total: items.length,
      page,
      limit,
      pages: 1,
    },
  };
}

export const mockBackendCap = {
  id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
  name: 'AWS monthly',
  scope: 'platform' as const,
  scope_value: 'aws',
  cap_amount: 10000,
  period: 'monthly',
  is_active: true,
  created_at: '2026-11-01T00:00:00+00:00',
  updated_at: '2026-11-01T00:00:00+00:00',
  current_month_spend: 4500,
  pct_used: 45,
};

export const mockBackendTeamMember = {
  id: 'dddddddd-dddd-dddd-dddd-dddddddddddd',
  user_id: MOCK_USER_ID,
  email: 'finops@example.com',
  name: 'FinOps User',
  role: 'owner' as const,
  invite_accepted: true,
  created_at: '2026-11-01T00:00:00+00:00',
};

export const mockBackendRecommendation = {
  id: 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
  type: 'rightsizing',
  title: 'Downsize idle instance',
  description: 'CPU under 5%',
  savings_usd: 240,
  confidence: 'high',
  status: 'open',
  created_at: '2026-11-01T00:00:00+00:00',
  metadata: { provider: 'aws', service: 'AmazonEC2', region: 'us-east-1' },
};
