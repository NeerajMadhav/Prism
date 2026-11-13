import { describe, expect, it } from 'vitest';

import { safeRedirectPath } from '@/lib/utils/safeRedirect';

describe('safeRedirectPath', () => {
  it('allows same-origin relative paths', () => {
    expect(safeRedirectPath('/dashboard', '/')).toBe('/dashboard');
    expect(safeRedirectPath('/costs?tab=day', '/')).toBe('/costs?tab=day');
  });

  it('blocks open redirects', () => {
    expect(safeRedirectPath('//evil.com', '/dashboard')).toBe('/dashboard');
    expect(safeRedirectPath('/\\evil.com', '/dashboard')).toBe('/dashboard');
    expect(safeRedirectPath('https://evil.com', '/dashboard')).toBe('/dashboard');
    expect(safeRedirectPath('dashboard', '/dashboard')).toBe('/dashboard');
  });
});
