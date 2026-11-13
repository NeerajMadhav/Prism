'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useCaps } from '@/lib/hooks/useCaps';
import { useOrg } from '@/lib/hooks/useOrg';
import { formatCurrency } from '@/lib/utils/currency';

export default function CapsPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useCaps(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Budget caps" description="Spend guardrails and alert thresholds." />
      {!orgId ? <EmptyState title="No organization" message="Sign in again." /> : null}
      {orgId && isLoading ? <LoadingSkeleton variant="table" /> : null}
      {orgId && isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {orgId && data && data.items.length === 0 ? (
        <EmptyState title="No budget caps" message="Create a cap to enable threshold alerts." />
      ) : null}
      {orgId && data && data.items.length > 0 ? (
        <ul className="divide-y rounded-lg border text-sm">
          {data.items.map((cap) => (
            <li key={cap.id} className="flex items-center justify-between px-4 py-3">
              <span className="font-medium">{cap.name}</span>
              <span className="font-mono">{formatCurrency(cap.amount, org?.currency ?? 'USD')}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
