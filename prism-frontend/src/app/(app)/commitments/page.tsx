'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { ProviderBadge } from '@/components/common/ProviderBadge';
import { useCommitments } from '@/lib/hooks/useCommitments';
import { useOrg } from '@/lib/hooks/useOrg';

export default function CommitmentsPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useCommitments(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Commitments" description="Reserved instances, savings plans, and utilization." />
      {!orgId ? <EmptyState title="No organization" message="Sign in again." /> : null}
      {orgId && isLoading ? <LoadingSkeleton variant="table" /> : null}
      {orgId && isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {orgId && data && data.items.length === 0 ? (
        <EmptyState title="No commitments" message="Nothing matched your filters." />
      ) : null}
      {orgId && data && data.items.length > 0 ? (
        <div className="rounded-lg border divide-y text-sm">
          {data.items.map((item) => (
            <div key={item.id} className="flex items-center justify-between gap-2 px-4 py-3">
              <div>
                <p className="font-medium">{item.resource_type}</p>
                <p className="text-muted-foreground">{item.type.replaceAll('_', ' ')}</p>
              </div>
              <ProviderBadge provider={item.provider} />
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
