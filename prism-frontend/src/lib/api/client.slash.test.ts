import { describe, expect, it } from 'vitest';

import { ensureTrailingSlashPath } from '@/lib/api/paths';

describe('ensureTrailingSlashPath', () => {
  it('adds slash to FastAPI collection roots', () => {
    expect(ensureTrailingSlashPath('/orgs/1/forecasts')).toBe('/orgs/1/forecasts/');
    expect(ensureTrailingSlashPath('/orgs/1/metrics?x=1')).toBe('/orgs/1/metrics/?x=1');
    expect(ensureTrailingSlashPath('/orgs/1/scorecard')).toBe('/orgs/1/scorecard/');
  });

  it('leaves accounts/team and already-slashed paths alone', () => {
    expect(ensureTrailingSlashPath('/orgs/1/accounts')).toBe('/orgs/1/accounts');
    expect(ensureTrailingSlashPath('/orgs/1/team')).toBe('/orgs/1/team');
    expect(ensureTrailingSlashPath('/orgs/1/caps/')).toBe('/orgs/1/caps/');
    expect(ensureTrailingSlashPath('/orgs/1/caps/abc')).toBe('/orgs/1/caps/abc');
  });
});
