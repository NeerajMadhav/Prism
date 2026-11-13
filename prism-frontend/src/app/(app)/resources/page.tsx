'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { ProviderBadge } from '@/components/common/ProviderBadge';
import { useResources } from '@/lib/hooks/useResources';
import { useOrg } from '@/lib/hooks/useOrg';

export default function ResourcesPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useResources(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Resources" description="Inventory across connected accounts." />
      {!orgId ? <EmptyState title="No organization" message="Sign in again." /> : null}
      {orgId && isLoading ? <LoadingSkeleton variant="table" /> : null}
      {orgId && isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {orgId && data && data.items.length === 0 ? (
        <EmptyState title="No resources" message="Sync accounts to populate inventory." />
      ) : null}
      {orgId && data && data.items.length > 0 ? (
        <ul className="divide-y rounded-lg border text-sm">
          {data.items.map((resource) => (
            <li key={resource.id} className="flex items-center justify-between gap-2 px-4 py-3">
              <div>
                <p className="font-medium">{resource.name}</p>
                <p className="text-muted-foreground">
                  {resource.type} · {resource.region}
                </p>
              </div>
              <ProviderBadge provider={resource.provider} />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
