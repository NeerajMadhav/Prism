'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useOrg } from '@/lib/hooks/useOrg';
import { useVirtualTags } from '@/lib/hooks/useVirtualTags';

export default function VirtualTagsPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useVirtualTags(orgId);

  return (
    <>
      <PageHeader
        title="Virtual tags"
        description="Rules for enriching cost allocation tags."
      />
      {!orgId ? (
        <EmptyState title="No organization" message="Sign in again if this persists." />
      ) : null}
      {orgId && isLoading ? <LoadingSkeleton variant="table" /> : null}
      {orgId && isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {orgId && data && data.items.length === 0 ? (
        <EmptyState title="No virtual tag rules" message="Nothing to show yet." />
      ) : null}
      {orgId && data && data.items.length > 0 ? (
        <div className="rounded-lg border p-4">
          <p className="mb-2 text-sm text-muted-foreground">{data.total} total</p>
          <ul className="divide-y text-sm">
            {data.items.map((item) => (
              <li key={item.id} className="py-2">
                {item.tag_key}={item.tag_value}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
