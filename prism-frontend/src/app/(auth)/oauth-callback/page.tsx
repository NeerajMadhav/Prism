'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useRef } from 'react';

import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { ROUTES } from '@/lib/constants/routes';
import { useExchangeOAuth } from '@/lib/hooks/useAuth';

function OAuthCallbackContent() {
  const params = useSearchParams();
  const code = params.get('code') ?? '';
  const state = params.get('state') ?? '';
  const exchange = useExchangeOAuth();
  const started = useRef(false);

  useEffect(() => {
    if (!code || !state || started.current) return;
    started.current = true;
    exchange.mutate({ code, state });
  }, [code, state, exchange]);

  return (
    <div className="space-y-4 text-center">
      {exchange.isPending ? <LoadingSkeleton /> : null}
      {exchange.isError ? (
        <>
          <p className="text-sm text-destructive">OAuth sign-in failed.</p>
          <Button variant="outline" render={<Link href={ROUTES.login} />}>
            Back to sign in
          </Button>
        </>
      ) : null}
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <AuthSplitLayout title="Completing sign in" subtitle="Finishing Google authentication">
      <Suspense fallback={<LoadingSkeleton />}>
        <OAuthCallbackContent />
      </Suspense>
    </AuthSplitLayout>
  );
}
