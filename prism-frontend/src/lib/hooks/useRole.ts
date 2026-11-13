/** PRISM FinOps — role helpers. */

'use client';

import { isAtLeast, ROLE_RANK } from '@/lib/auth/guards';
import { useAuthStore } from '@/lib/store/authStore';
import type { Role } from '@/types/api';

/** Current org role from auth store. */
export function useRole(): Role | null {
  return useAuthStore((s) => s.role);
}

/** True when current role rank is at least the required role. */
export function useIsAtLeast(required: Role): boolean {
  const role = useRole();
  if (!role) return false;
  return isAtLeast(role, required);
}

export { ROLE_RANK };
