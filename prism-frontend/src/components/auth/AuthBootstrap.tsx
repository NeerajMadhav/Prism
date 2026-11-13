/** PRISM FinOps — session bootstrap on app load. */

'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState, type ReactNode } from 'react';

import { AppSkeleton } from '@/components/layout/AppSkeleton';
import * as authApi from '@/lib/api/auth';
import { refreshAccessToken } from '@/lib/api/client';
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  scheduleProactiveRefresh,
} from '@/lib/auth/tokens';
import { useAuthStore } from '@/lib/store/authStore';
import { wsClient } from '@/lib/ws/wsClient';

const SESSION_ACTIVE_KEY = 'prism_session_active';

export type AuthBootstrapState = 'initializing' | 'authenticated' | 'unauthenticated';

interface AuthBootstrapProps {
  children: ReactNode;
}

/** Restores tokens after refresh, schedules proactive refresh, syncs multi-tab logout. */
export function AuthBootstrap({ children }: AuthBootstrapProps) {
  const [state, setState] = useState<AuthBootstrapState>('initializing');
  const setAuth = useAuthStore((s) => s.setAuth);
  const clear = useAuthStore((s) => s.clear);
  const setReady = useAuthStore((s) => s.setReady);
  const router = useRouter();

  useEffect(() => {
    let refreshCleanup: (() => void) | undefined;
    let cancelled = false;

    const scheduleRefresh = (accessToken: string) => {
      refreshCleanup?.();
      refreshCleanup = scheduleProactiveRefresh(accessToken, async () => {
        // Must share single-flight with 401 interceptor (refresh tokens rotate atomically).
        await refreshAccessToken();
        const next = getAccessToken();
        if (next) {
          scheduleRefresh(next);
        }
      });
    };

    async function bootstrap() {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        if (!cancelled) {
          setState('unauthenticated');
          setReady(true);
        }
        return;
      }
      try {
        const access = await refreshAccessToken();
        const me = await authApi.getMe();
        if (cancelled) {
          return;
        }
        setAuth(me.user, me.org, me.role);
        scheduleRefresh(access);
        setState('authenticated');
      } catch {
        clearTokens();
        clear();
        if (!cancelled) {
          setState('unauthenticated');
        }
      } finally {
        if (!cancelled) {
          setReady(true);
        }
      }
    }

    void bootstrap();

    const onStorage = (event: StorageEvent) => {
      if (event.key === SESSION_ACTIVE_KEY && event.newValue === '0') {
        clearTokens();
        clear();
        wsClient.disconnect(true);
        router.push('/login');
      }
    };
    window.addEventListener('storage', onStorage);

    return () => {
      cancelled = true;
      refreshCleanup?.();
      window.removeEventListener('storage', onStorage);
    };
  }, [clear, router, setAuth, setReady]);

  if (state === 'initializing') {
    return <AppSkeleton />;
  }

  return <>{children}</>;
}
