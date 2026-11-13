'use client';

import { DataCard } from '@/components/common/DataCard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useScorecard } from '@/lib/hooks/useScorecard';
import { useOrg } from '@/lib/hooks/useOrg';

export default function ScorecardPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useScorecard(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="FinOps scorecard" description="Efficiency and maturity snapshot." />
      {!orgId ? <EmptyState title="No organization" message="Sign in again." /> : null}
      {orgId && isLoading ? <LoadingSkeleton variant="kpi-row" /> : null}
      {orgId && isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {orgId && data ? (
        <div className="grid gap-4 md:grid-cols-3">
          <DataCard title="Total score" value={data.total_score} />
          <DataCard title="Grade" value={data.grade} />
          <DataCard title="Metrics tracked" value={data.metrics.length} />
        </div>
      ) : null}
    </div>
  );
}
