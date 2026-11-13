import { describe, expect, it } from 'vitest';

import { normalizeResource } from '@/lib/api/resources';

describe('normalizeResource', () => {
  it('maps resource_type and last_cost_usd', () => {
    const resource = normalizeResource({
      id: 'r1',
      provider: 'aws',
      resource_id: 'i-abc',
      resource_type: 'ec2',
      name: 'web-1',
      region: 'us-east-1',
      tags: { env: 'prod' },
      last_cost_usd: 12.5,
      is_idle: true,
      idle_since: '2026-11-01T00:00:00+00:00',
      last_seen: '2026-11-13T00:00:00+00:00',
    });
    expect(resource.type).toBe('ec2');
    expect(resource.cost_per_day).toBe(12.5);
    expect(resource.is_idle).toBe(true);
    expect(resource.last_active_at).toBe('2026-11-13T00:00:00+00:00');
  });
});
