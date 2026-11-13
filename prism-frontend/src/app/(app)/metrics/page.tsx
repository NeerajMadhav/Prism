'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useMetrics } from '@/lib/hooks/useMetrics';
import { useOrg } from '@/lib/hooks/useOrg';

export default function MetricsPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useMetrics(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Business metrics" description="Drivers for unit economics." />
      {!orgId ? <EmptyState title="No organization" message="Sign in again." /> : null}
      {orgId && isLoading ? <LoadingSkeleton variant="table" /> : null}
      {orgId && isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {orgId && data && data.items.length === 0 ? (
        <EmptyState title="No metrics" message="Define business metrics to track unit costs." />
      ) : null}
      {orgId && data && data.items.length > 0 ? (
        <ul className="divide-y rounded-lg border text-sm">
          {data.items.map((metric) => (
            <li key={metric.id} className="flex justify-between px-4 py-3">
              <span className="font-medium">{metric.name}</span>
              <span className="text-muted-foreground">{metric.unit}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
