'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useRecommendations } from '@/lib/hooks/useRecommendations';
import { useOrg } from '@/lib/hooks/useOrg';
import { formatCurrency } from '@/lib/utils/currency';

export default function RecommendationsPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useRecommendations(orgId, {
    status: 'open',
  });

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Recommendations" description="Open savings opportunities." />
      {!orgId ? <EmptyState title="No organization" message="Sign in again." /> : null}
      {orgId && isLoading ? <LoadingSkeleton variant="table" /> : null}
      {orgId && isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {orgId && data && data.items.length === 0 ? (
        <EmptyState title="No recommendations" message="You're all caught up." />
      ) : null}
      {orgId && data && data.items.length > 0 ? (
        <ul className="divide-y rounded-lg border text-sm">
          {data.items.map((rec) => (
            <li key={rec.id} className="flex items-center justify-between gap-2 px-4 py-3">
              <div>
                <p className="font-medium">{rec.title}</p>
                <p className="text-muted-foreground">{rec.service}</p>
              </div>
              <span className="font-mono text-success">
                {formatCurrency(rec.estimated_savings_monthly, org?.currency ?? 'USD', true)}/mo
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
