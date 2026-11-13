/** PRISM FinOps — cloud accounts list. */

'use client';

import Link from 'next/link';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { RoleGate } from '@/components/common/RoleGate';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ROUTES } from '@/lib/constants/routes';
import { useAccounts, useTriggerSync } from '@/lib/hooks/useAccounts';
import { useAuthStore } from '@/lib/store/authStore';

export default function AccountsPage() {
  const orgId = useAuthStore((s) => s.org?.id);
  const { data, isLoading, isError, refetch } = useAccounts(orgId);
  const sync = useTriggerSync(orgId);
  const items = data?.items ?? [];

  return (
    <div className="animate-slide-up space-y-6">
      <PageHeader
        title="Cloud Accounts"
        description="Connected AWS, Azure, and GCP billing sources"
        actions={
          <RoleGate minRole="admin">
            <Button render={<Link href={ROUTES.accountsConnect} />}>Connect Account</Button>
          </RoleGate>
        }
      />

      {isLoading ? <LoadingSkeleton variant="card" /> : null}
      {isError ? <ErrorState retry={() => void refetch()} /> : null}
      {!isLoading && !isError && items.length === 0 ? (
        <EmptyState
          title="No cloud accounts connected"
          message="Connect AWS, Azure, or GCP to start tracking your cloud spend."
          action={{
            label: 'Connect Account →',
            onClick: () => {
              window.location.href = ROUTES.accountsConnect;
            },
          }}
        />
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map((account) => (
          <Card key={account.id}>
            <CardContent className="space-y-3 pt-(--card-spacing)">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <Link
                    href={ROUTES.accountDetail(account.id)}
                    className="font-semibold hover:text-brand-600"
                  >
                    {account.name}
                  </Link>
                  <p className="text-xs uppercase text-muted-foreground">{account.provider}</p>
                </div>
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{account.last_sync_status}</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Records: {account.records_synced?.toLocaleString?.() ?? '—'}
              </p>
              <RoleGate minRole="admin">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={sync.isPending}
                  onClick={() => sync.mutate(account.id)}
                >
                  Sync Now
                </Button>
              </RoleGate>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
