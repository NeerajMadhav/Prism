/** PRISM FinOps — role labels and ordering constants. */

import { ROLE_RANK } from '@/lib/auth/guards';
import type { Role } from '@/types/api';

export const ROLE_LABELS: Record<Role, string> = {
  viewer: 'Viewer',
  editor: 'Editor',
  admin: 'Admin',
  owner: 'Owner',
};

export const ROLES_BY_RANK: Role[] = (Object.keys(ROLE_RANK) as Role[]).sort(
  (a, b) => ROLE_RANK[a] - ROLE_RANK[b],
);
