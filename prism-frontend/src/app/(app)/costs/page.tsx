/** PRISM FinOps — costs explorer with clear day-wise + provider breakdown. */

'use client';

import { useMemo } from 'react';

import { DataCard } from '@/components/common/DataCard';
import { DeltaBadge } from '@/components/common/DeltaBadge';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { EstimatedBadge } from '@/components/common/EstimatedBadge';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { ProviderBadge } from '@/components/common/ProviderBadge';
import {
  useCostSummary,
  useCostsByDay,
  useTopServices,
} from '@/lib/hooks/useCosts';
import { useOrg } from '@/lib/hooks/useOrg';
import { formatCurrency } from '@/lib/utils/currency';
import { ALL_PROVIDERS, getProviderLabel } from '@/lib/utils/providers';
import type { Provider } from '@/types/api';

export default function CostsPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const currency = org?.currency ?? 'USD';
  const summary = useCostSummary(orgId);
  const byDay = useCostsByDay(orgId);
  const services = useTopServices(orgId);
  const loading = summary.isLoading || byDay.isLoading || services.isLoading;

  const activeProviders = useMemo(() => {
    const seen = new Set<Provider>();
    for (const day of byDay.data ?? []) {
      for (const provider of ALL_PROVIDERS) {
        if ((day.by_provider?.[provider] ?? 0) > 0) {
          seen.add(provider);
        }
      }
    }
    if (seen.size === 0) {
      for (const svc of services.data ?? []) {
        seen.add(svc.provider);
      }
    }
    return ALL_PROVIDERS.filter((p) => seen.has(p));
  }, [byDay.data, services.data]);

  const providersForTable = activeProviders.length > 0 ? activeProviders : (['aws'] as Provider[]);

  return (
    <div className="animate-slide-up space-y-6">
      <PageHeader
        title="Costs"
        description="Day-by-day cloud spend (UTC calendar days). AWS, Azure, and GCP shown as separate columns when present."
      />
      {!orgId ? (
        <EmptyState title="No organization" message="Sign in again if this persists." />
      ) : null}
      {orgId && loading ? <LoadingSkeleton variant="kpi-row" /> : null}
      {orgId && (summary.isError || byDay.isError || services.isError) ? (
        <ErrorState
          error={summary.error ?? byDay.error ?? services.error}
          retry={() => {
            void summary.refetch();
            void byDay.refetch();
            void services.refetch();
          }}
        />
      ) : null}

      {orgId && summary.data ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <DataCard
            title="Month-to-date"
            value={formatCurrency(summary.data.total, summary.data.currency)}
            subtitle={
              <div className="flex items-center gap-2">
                <DeltaBadge pct={summary.data.mom_pct} />
                <EstimatedBadge show={summary.data.is_estimate} />
              </div>
            }
          />
          <DataCard
            title="Days with spend"
            value={(byDay.data ?? []).filter((d) => d.total > 0).length}
            subtitle="UTC billing days this month"
          />
        </div>
      ) : null}

      {orgId && byDay.data && byDay.data.length === 0 ? (
        <EmptyState
          title="No daily cost series"
          message="Connect a cloud account and sync billing to see day-wise spend."
        />
      ) : null}

      {orgId && byDay.data && byDay.data.length > 0 ? (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-medium text-muted-foreground">
              Daily spend by provider (UTC)
            </h2>
            <div className="flex flex-wrap gap-2">
              {providersForTable.map((provider) => (
                <ProviderBadge key={provider} provider={provider} />
              ))}
            </div>
          </div>
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full min-w-[32rem] text-left text-sm">
              <thead className="border-b bg-muted/40 text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Date</th>
                  {providersForTable.map((provider) => (
                    <th key={provider} className="px-4 py-2 font-medium">
                      {getProviderLabel(provider)}
                    </th>
                  ))}
                  <th className="px-4 py-2 font-medium">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {[...byDay.data].reverse().map((day) => (
                  <tr key={day.date} className="hover:bg-muted/20">
                    <td className="px-4 py-2 font-mono tabular-nums">{day.date}</td>
                    {providersForTable.map((provider) => (
                      <td key={provider} className="px-4 py-2 font-mono tabular-nums">
                        {formatCurrency(day.by_provider?.[provider] ?? 0, currency)}
                      </td>
                    ))}
                    <td className="px-4 py-2 font-mono tabular-nums font-medium">
                      {formatCurrency(day.total, currency)}
                      {day.is_estimate ? (
                        <span className="ml-2 text-xs text-muted-foreground">est.</span>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-muted-foreground">
            Each row is one UTC calendar day. Provider columns stay aligned so AWS, Azure, and GCP
            are comparable side by side.
          </p>
        </section>
      ) : null}

      {orgId && services.data && services.data.length === 0 && (byDay.data?.length ?? 0) === 0 ? (
        <EmptyState title="No cost data" message="Connect an account to ingest billing." />
      ) : null}
      {orgId && services.data && services.data.length > 0 ? (
        <section className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">Top services</h2>
          <div className="rounded-lg border">
            <ul className="divide-y text-sm">
              {services.data.map((svc) => (
                <li
                  key={`${svc.provider}-${svc.service}`}
                  className="flex items-center justify-between gap-3 px-4 py-3"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <ProviderBadge provider={svc.provider} />
                    <span className="truncate">{svc.service}</span>
                  </div>
                  <span className="shrink-0 font-mono">
                    {formatCurrency(svc.total, currency)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      ) : null}
    </div>
  );
}
