import { describe, expect, it } from 'vitest';

import { normalizeAccount } from '@/lib/api/accounts';
import { mockBackendAccount } from '@/test/mocks/backend';

describe('normalizeAccount', () => {
  it('maps display_name → name and last_sync → last_sync_at', () => {
    const account = normalizeAccount(mockBackendAccount);
    expect(account.name).toBe('Prod AWS');
    expect(account.last_sync_at).toBe('2026-11-13T10:00:00+00:00');
    expect(account.provider_account_id).toBe('123456789012');
    expect(account.last_sync_status).toBe('success');
    expect(account.error_message).toBeUndefined();
  });

  it('maps error status aliases', () => {
    const account = normalizeAccount({
      ...mockBackendAccount,
      last_sync_status: 'error',
      last_sync_error: 'IAM denied',
    });
    expect(account.last_sync_status).toBe('failed');
    expect(account.error_message).toBe('IAM denied');
  });
});
