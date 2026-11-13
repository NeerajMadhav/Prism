import { describe, expect, it } from 'vitest';

import { normalizeTeamMember } from '@/lib/api/team';

describe('normalizeTeamMember', () => {
  it('maps created_at → joined_at', () => {
    const member = normalizeTeamMember({
      id: 'm1',
      user_id: 'u1',
      email: 'owner@example.com',
      name: 'Owner',
      role: 'owner',
      invite_accepted: true,
      created_at: '2026-11-01T00:00:00+00:00',
    });
    expect(member.joined_at).toBe('2026-11-01T00:00:00+00:00');
    expect(member.role).toBe('owner');
  });
});
