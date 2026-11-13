/** PRISM FinOps — role rank helpers for programmatic guards. */

import type { Role } from '@/types/api';

export const ROLE_RANK: Record<Role, number> = {
  viewer: 1,
  editor: 2,
  admin: 3,
  owner: 4,
};

/** Returns true when `role` meets or exceeds `required`. */
export function isAtLeast(role: Role | null | undefined, required: Role): boolean {
  if (!role) {
    return false;
  }
  return ROLE_RANK[role] >= ROLE_RANK[required];
}
