import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

import { clientLogger, createClientRequestId } from '@/lib/observability/logger';

describe('clientLogger', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    vi.spyOn(console, 'info').mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('emits structured JSON without throwing', () => {
    clientLogger.error('api_error', { status: 500, path: '/orgs/x/costs' });
    expect(console.error).toHaveBeenCalled();
    const line = String(vi.mocked(console.error).mock.calls[0]?.[0]);
    const parsed = JSON.parse(line) as { event: string; service: string };
    expect(parsed.event).toBe('api_error');
    expect(parsed.service).toBe('prism-frontend');
  });

  it('creates a non-empty request id', () => {
    expect(createClientRequestId().length).toBeGreaterThan(8);
  });
});
