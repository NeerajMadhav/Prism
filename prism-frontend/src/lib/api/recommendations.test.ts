import { describe, expect, it } from 'vitest';

import { normalizeRecommendation } from '@/lib/api/recommendations';

describe('normalizeRecommendation', () => {
  it('maps savings_usd → estimated_savings_monthly', () => {
    const rec = normalizeRecommendation({
      id: 'r1',
      type: 'rightsizing',
      title: 'Downsize i-123',
      description: 'CPU low',
      savings_usd: 120,
      confidence: 'high',
      status: 'open',
      created_at: '2026-11-01T00:00:00+00:00',
      metadata: { provider: 'aws', service: 'AmazonEC2', region: 'us-east-1' },
    });
    expect(rec.estimated_savings_monthly).toBe(120);
    expect(rec.provider).toBe('aws');
    expect(rec.service).toBe('AmazonEC2');
    expect(rec.confidence).toBe('high');
  });
});
