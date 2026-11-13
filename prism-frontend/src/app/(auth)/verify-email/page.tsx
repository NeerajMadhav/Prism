'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useRef } from 'react';

import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { ROUTES } from '@/lib/constants/routes';
import { useVerifyEmail } from '@/lib/hooks/useAuth';

function VerifyEmailContent() {
  const params = useSearchParams();
  const token = params.get('token') ?? '';
  const userId = params.get('user_id') ?? params.get('userId') ?? '';
  const verify = useVerifyEmail();
  const started = useRef(false);

  useEffect(() => {
    if (!token || !userId || started.current) return;
    started.current = true;
    verify.mutate({ token, user_id: userId });
  }, [token, userId, verify]);

  return (
    <div className="space-y-4 text-center">
      {!token || !userId ? (
        <p className="text-sm text-destructive">Verification link is incomplete.</p>
      ) : verify.isPending ? (
        <LoadingSkeleton />
      ) : verify.isError ? (
        <p className="text-sm text-destructive">Invalid or expired verification link.</p>
      ) : verify.isSuccess ? (
        <p className="text-sm text-muted-foreground">Email verified. Redirecting…</p>
      ) : null}
      <Button variant="outline" render={<Link href={ROUTES.login} />}>
        Back to sign in
      </Button>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <AuthSplitLayout title="Verify email" subtitle="Confirming your email address">
      <Suspense fallback={<LoadingSkeleton />}>
        <VerifyEmailContent />
      </Suspense>
    </AuthSplitLayout>
  );
}
