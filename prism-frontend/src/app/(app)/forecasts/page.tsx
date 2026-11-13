'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useForecasts } from '@/lib/hooks/useForecasts';
import { useOrg } from '@/lib/hooks/useOrg';
import { formatCurrency } from '@/lib/utils/currency';

export default function ForecastsPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useForecasts(orgId);

  return (
    <>
      <PageHeader title="Forecasts" description="Projected spend for the current period." />
      {!orgId ? (
        <EmptyState title="No organization" message="Sign in again if this persists." />
      ) : null}
      {orgId && isLoading ? <LoadingSkeleton variant="table" /> : null}
      {orgId && isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {orgId && data && data.length === 0 ? (
        <EmptyState title="No forecast yet" message="Nothing to show yet." />
      ) : null}
      {orgId && data && data.length > 0 ? (
        <div className="rounded-lg border p-4">
          <ul className="space-y-2 text-sm">
            {data.map((row) => (
              <li key={row.provider} className="flex justify-between border-b py-2">
                <span className="capitalize">{row.provider}</span>
                <span className="font-mono">
                  {formatCurrency(row.projected_total, row.currency, true)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
