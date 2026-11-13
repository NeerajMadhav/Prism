import { describe, expect, it } from 'vitest';

import { normalizeCap } from '@/lib/api/caps';

describe('normalizeCap', () => {
  it('maps cap_amount and current_month_spend into UI fields', () => {
    const cap = normalizeCap({
      id: 'c1',
      name: 'AWS monthly',
      scope: 'platform',
      scope_value: 'aws',
      cap_amount: 10000,
      period: 'monthly',
      is_active: true,
      created_at: '2026-11-01T00:00:00+00:00',
      current_month_spend: 4500,
      pct_used: 45,
    });
    expect(cap.amount).toBe(10000);
    expect(cap.current_spend).toBe(4500);
    expect(cap.pct_used).toBe(45);
    expect(cap.provider).toBe('aws');
    expect(cap.next_threshold).toBe(50);
  });

  it('maps service and account scopes', () => {
    expect(
      normalizeCap({
        id: 'c2',
        name: 'EC2',
        scope: 'service',
        scope_value: 'AmazonEC2',
        cap_amount: 1,
        period: 'monthly',
        is_active: true,
        created_at: '2026-11-01T00:00:00+00:00',
      }).service,
    ).toBe('AmazonEC2');
    expect(
      normalizeCap({
        id: 'c3',
        name: 'Acct',
        scope: 'account',
        scope_value: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        cap_amount: 1,
        period: 'monthly',
        is_active: true,
        created_at: '2026-11-01T00:00:00+00:00',
      }).account_id,
    ).toBe('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
  });
});
