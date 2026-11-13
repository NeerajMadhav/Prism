import { describe, expect, it } from 'vitest';

import { normalizeAlert } from '@/lib/api/alerts';
import { mockBackendAlert } from '@/test/mocks/backend';

describe('normalizeAlert', () => {
  it('derives active status when unacknowledged', () => {
    const alert = normalizeAlert(mockBackendAlert);
    expect(alert.status).toBe('active');
    expect(alert.threshold_pct).toBe(90);
  });

  it('derives acknowledged status', () => {
    const alert = normalizeAlert({
      ...mockBackendAlert,
      acknowledged_at: '2026-11-13T09:00:00+00:00',
    });
    expect(alert.status).toBe('acknowledged');
  });

  it('derives snoozed status when snooze is in the future', () => {
    const alert = normalizeAlert({
      ...mockBackendAlert,
      snoozed_until: '2099-01-01T00:00:00+00:00',
    });
    expect(alert.status).toBe('snoozed');
  });
});
