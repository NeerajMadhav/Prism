/** PRISM FinOps — role-based render gate. */

'use client';

import type { ReactNode } from 'react';

import { useIsAtLeast } from '@/lib/hooks/useRole';
import type { Role } from '@/types/api';

interface RoleGateProps {
  minRole: Role;
  children: ReactNode;
  fallback?: ReactNode;
}

export function RoleGate({ minRole, children, fallback = null }: RoleGateProps) {
  const allowed = useIsAtLeast(minRole);
  if (!allowed) {
    return fallback;
  }
  return children;
}
