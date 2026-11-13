/** PRISM FinOps — authenticated user identity store. */

import { create } from 'zustand';

import type { Role } from '@/types/api';
import type { Org, User } from '@/types/auth';

interface AuthState {
  user: User | null;
  org: Org | null;
  role: Role | null;
  isReady: boolean;
  setAuth: (user: User, org: Org, role: Role) => void;
  clear: () => void;
  setReady: (ready: boolean) => void;
}

/** Zustand store for session identity (not persisted). */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  org: null,
  role: null,
  isReady: false,
  setAuth: (user, org, role) =>
    set({ user, org, role, isReady: true }),
  clear: () => set({ user: null, org: null, role: null, isReady: true }),
  setReady: (ready) => set({ isReady: ready }),
}));
