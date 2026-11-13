/** PRISM FinOps — account detail. */

'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';

import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { Button } from '@/components/ui/button';
import { ROUTES } from '@/lib/constants/routes';
import { useAccount, useSyncLogs } from '@/lib/hooks/useAccounts';
import { useAuthStore } from '@/lib/store/authStore';

export default function AccountDetailPage() {
  const params = useParams<{ id: string }>();
  const orgId = useAuthStore((s) => s.org?.id);
  const accountId = params.id;
  const account = useAccount(orgId, accountId);
  const logs = useSyncLogs(orgId, accountId, true);

  if (account.isLoading) return <LoadingSkeleton />;
  if (account.isError || !account.data) {
    return <ErrorState retry={() => void account.refetch()} />;
  }

  return (
    <div className="animate-slide-up space-y-6">
      <PageHeader
        title={account.data.name}
        description={`${account.data.provider.toUpperCase()} · ${account.data.last_sync_status}`}
        actions={
          <Button variant="outline" render={<Link href={ROUTES.accounts} />}>
            All accounts
          </Button>
        }
      />
      <div className="rounded-xl border border-border bg-card p-4">
        <h2 className="mb-3 text-sm font-semibold">Sync logs</h2>
        <ul className="space-y-2 text-sm">
          {(logs.data?.items ?? []).map((log) => (
            <li key={log.id} className="flex justify-between border-b border-border py-2 last:border-0">
              <span>{log.status}</span>
              <span className="text-muted-foreground">{log.started_at}</span>
            </li>
          ))}
          {(logs.data?.items.length ?? 0) === 0 ? (
            <li className="text-muted-foreground">No sync history yet</li>
          ) : null}
        </ul>
      </div>
    </div>
  );
}
