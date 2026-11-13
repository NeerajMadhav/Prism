/** PRISM FinOps — authenticated app chrome. */

'use client';

import { useRouter } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';

import { AppSkeleton } from '@/components/layout/AppSkeleton';
import { HealthBanner } from '@/components/layout/HealthBanner';
import { OfflineBanner } from '@/components/layout/OfflineBanner';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { getRefreshToken } from '@/lib/auth/tokens';
import { ROUTES } from '@/lib/constants/routes';
import { useMe } from '@/lib/hooks/useAuth';
import { useHealth } from '@/lib/hooks/useHealth';
import { useWebSocket } from '@/lib/hooks/useWebSocket';
import { useAuthStore } from '@/lib/store/authStore';

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isReady = useAuthStore((s) => s.isReady);
  const me = useMe();
  useWebSocket();
  useHealth();

  useEffect(() => {
    if (!isReady && !me.isLoading) {
      useAuthStore.getState().setReady(true);
    }
  }, [isReady, me.isLoading]);

  useEffect(() => {
    if (me.isLoading) {
      return;
    }
    const hasToken = Boolean(getRefreshToken());
    if (!user && !hasToken) {
      router.replace(ROUTES.login);
    }
  }, [me.isLoading, router, user]);

  if (me.isLoading && !user) {
    return <AppSkeleton />;
  }

  if (!user) {
    return <AppSkeleton />;
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <OfflineBanner />
        <HealthBanner />
        <TopBar />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
