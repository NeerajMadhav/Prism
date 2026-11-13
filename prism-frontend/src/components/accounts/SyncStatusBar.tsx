/** PRISM FinOps — dashboard sync status strip. */

'use client';

import Link from 'next/link';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ROUTES } from '@/lib/constants/routes';
import { useAccounts } from '@/lib/hooks/useAccounts';
import { useAuthStore } from '@/lib/store/authStore';

export function SyncStatusBar() {
  const orgId = useAuthStore((s) => s.org?.id);
  const { data, isLoading } = useAccounts(orgId);
  const items = data?.items ?? [];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">Sync status</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2 text-sm">
          {isLoading ? <span className="text-muted-foreground">Loading…</span> : null}
          {!isLoading && items.length === 0 ? (
            <span className="text-muted-foreground">No accounts connected</span>
          ) : null}
          {items.map((account) => (
            <span key={account.id} className="rounded-md border border-border px-2 py-1">
              {account.provider.toUpperCase()} · {account.last_sync_status}
            </span>
          ))}
        </div>
        <Link href={ROUTES.accounts} className="text-sm font-medium text-brand-600 hover:underline">
          Manage accounts
        </Link>
      </CardContent>
    </Card>
  );
}
