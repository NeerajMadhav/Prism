import { describe, expect, it, vi, beforeEach } from 'vitest';

/**
 * Documents the single-flight contract: concurrent refresh callers must share one
 * in-flight promise so atomic refresh-token rotation on the backend cannot logout
 * parallel dashboard requests.
 */
describe('refresh single-flight contract', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('dedupes overlapping refresh promises via shared latch pattern', async () => {
    let inflight: Promise<string> | null = null;
    let calls = 0;

    async function refreshOnce(): Promise<string> {
      if (inflight) return inflight;
      inflight = (async () => {
        calls += 1;
        await new Promise((r) => setTimeout(r, 20));
        return 'token-' + calls;
      })().finally(() => {
        inflight = null;
      });
      return inflight;
    }

    const [a, b, c] = await Promise.all([refreshOnce(), refreshOnce(), refreshOnce()]);
    expect(calls).toBe(1);
    expect(a).toBe(b);
    expect(b).toBe(c);
  });
});
