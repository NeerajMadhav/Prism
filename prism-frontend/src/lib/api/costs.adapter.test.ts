import { describe, expect, it, vi, beforeEach } from 'vitest';

import { mockCostSummary, mockTopServices, MOCK_ORG_ID } from '@/test/mocks/backend';

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { apiClient } from '@/lib/api/client';
import { getSummary, getTopServices } from '@/lib/api/costs';

describe('costs adapters (mock backend payloads)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('normalizes overall costs into UI CostSummary', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockCostSummary });
    const summary = await getSummary(MOCK_ORG_ID);
    expect(summary.total).toBe(12453.2);
    expect(summary.mom_pct).toBeCloseTo(((12453.2 - 11000) / 11000) * 100);
    expect(summary.data_as_of).toBe('2026-11-12');
  });

  it('normalizes top-services total_usd → total', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockTopServices });
    const rows = await getTopServices(MOCK_ORG_ID);
    expect(rows[0]).toMatchObject({
      service: 'AmazonEC2',
      total: 4200,
      rank: 1,
    });
  });
});
