import { describe, expect, it } from 'vitest';

import { passwordSchema } from '@/lib/validation/password';

describe('passwordSchema', () => {
  it('accepts backend-valid passwords', () => {
    expect(passwordSchema.safeParse('Secret1!').success).toBe(true);
  });

  it('rejects missing uppercase', () => {
    expect(passwordSchema.safeParse('secret1!').success).toBe(false);
  });

  it('rejects missing number', () => {
    expect(passwordSchema.safeParse('Secret!!').success).toBe(false);
  });

  it('rejects missing special char', () => {
    expect(passwordSchema.safeParse('Secret11').success).toBe(false);
  });

  it('rejects short passwords', () => {
    expect(passwordSchema.safeParse('Ab1!').success).toBe(false);
  });
});
