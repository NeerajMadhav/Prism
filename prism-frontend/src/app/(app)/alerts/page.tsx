/** PRISM FinOps — alerts inbox. */

'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useAlerts } from '@/lib/hooks/useAlerts';
import { useOrg } from '@/lib/hooks/useOrg';
import { formatRelative } from '@/lib/utils/dates';

export default function AlertsPage() {
  const org = useOrg();
  const orgId = org?.id;

  const { data, isLoading, isError, error, refetch } = useAlerts(orgId, { status: 'active' });

  return (
    <>
      <PageHeader
        title="Alerts"
        description="Showing active alerts. Use status filters when the list toolbar is added."
      />
      {!orgId ? (
        <EmptyState title="No organization" message="Sign in again if this persists." />
      ) : null}
      {orgId && isLoading ? <LoadingSkeleton variant="table" /> : null}
      {orgId && isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {orgId && data && data.items.length === 0 ? (
        <EmptyState title="No active alerts" message="You're all caught up." />
      ) : null}
      {orgId && data && data.items.length > 0 ? (
        <div className="rounded-lg border">
          <ul className="divide-y">
            {data.items.map((alert) => (
              <li key={alert.id} className="flex flex-wrap items-center justify-between gap-2 p-4 text-sm">
                <div>
                  <p className="font-medium">{alert.type.replaceAll('_', ' ')}</p>
                  <p className="text-muted-foreground">{formatRelative(alert.triggered_at)}</p>
                </div>
                <span className="capitalize text-muted-foreground">{alert.status}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
