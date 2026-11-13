'use client';

import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { ROUTES } from '@/lib/constants/routes';

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <h1 className="text-xl font-semibold">Something went wrong</h1>
      {process.env.NODE_ENV === 'development' ? (
        <p className="max-w-md text-sm text-muted-foreground">{error.message}</p>
      ) : null}
      <div className="flex gap-2">
        <Button type="button" onClick={reset}>
          Try again
        </Button>
        <Button variant="outline" render={<Link href={ROUTES.dashboard} />}>
          Dashboard
        </Button>
      </div>
    </div>
  );
}
