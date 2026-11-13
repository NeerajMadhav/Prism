/** PRISM FinOps — dashboard home. */

'use client';

import Link from 'next/link';

import { SyncStatusBar } from '@/components/accounts/SyncStatusBar';
import { DataCard } from '@/components/common/DataCard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { EstimatedBadge } from '@/components/common/EstimatedBadge';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { ProviderBadge } from '@/components/common/ProviderBadge';
import { ROUTES } from '@/lib/constants/routes';
import { useAccounts } from '@/lib/hooks/useAccounts';
import { useAlertsCount } from '@/lib/hooks/useAlerts';
import { useCostSummary } from '@/lib/hooks/useCosts';
import { useForecasts } from '@/lib/hooks/useForecasts';
import { useOrg } from '@/lib/hooks/useOrg';
import { useAuthStore } from '@/lib/store/authStore';
import { formatCurrency } from '@/lib/utils/currency';
import { getOrgNow } from '@/lib/utils/dates';

function greetingName(name: string, tz: string) {
  const hour = getOrgNow(tz).getHours();
  const salutation =
    hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  return `${salutation}, ${name.split(' ')[0]}`;
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const org = useOrg();
  const orgId = org?.id;

  const summary = useCostSummary(orgId);
  const alertsCount = useAlertsCount(orgId);
  const accounts = useAccounts(orgId);
  const forecasts = useForecasts(orgId ?? '');

  const loading =
    summary.isLoading || alertsCount.isLoading || accounts.isLoading || forecasts.isLoading;
  const error = summary.error ?? alertsCount.error ?? accounts.error ?? forecasts.error;
  const refetchAll = () => {
    void summary.refetch();
    void alertsCount.refetch();
    void accounts.refetch();
    void forecasts.refetch();
  };

  const forecastTotal = (forecasts.data ?? []).reduce(
    (sum, row) => sum + row.projected_total,
    0,
  );

  return (
    <>
      <PageHeader
        title={user ? greetingName(user.name, org?.timezone ?? 'UTC') : 'Dashboard'}
        description="Overview of spend, alerts, and connected accounts."
      />
      {!orgId ? (
        <EmptyState title="No organization" message="Sign in again if this persists." />
      ) : null}
      {orgId && loading ? <LoadingSkeleton variant="kpi-row" /> : null}
      {orgId && error ? <ErrorState error={error} retry={refetchAll} /> : null}
      {orgId && !loading && !error && summary.data ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <DataCard
              title="MTD spend"
              value={formatCurrency(summary.data.total, summary.data.currency, true)}
              subtitle={
                summary.data.mom_pct != null
                  ? `${summary.data.mom_pct > 0 ? '+' : ''}${summary.data.mom_pct.toFixed(1)}% vs last month`
                  : 'Month over month unavailable'
              }
              footer={summary.data.is_estimate ? <EstimatedBadge /> : null}
            />
            <DataCard
              title="Connected accounts"
              value={accounts.data?.items.length ?? 0}
              subtitle="Cloud billing sources"
            />
            <DataCard
              title="Active alerts"
              value={alertsCount.data?.active ?? 0}
              subtitle={
                <Link href={ROUTES.alerts} className="text-primary hover:underline">
                  View alerts
                </Link>
              }
            />
            <DataCard
              title="Forecast (month end)"
              value={formatCurrency(
                forecastTotal,
                org?.currency ?? summary.data.currency,
                true,
              )}
              subtitle={`${forecasts.data?.length ?? 0} provider projections`}
            />
          </div>
          <SyncStatusBar />
          {accounts.data && accounts.data.items.length > 0 ? (
            <div className="rounded-lg border p-4">
              <h2 className="mb-3 text-sm font-medium text-muted-foreground">Accounts</h2>
              <ul className="divide-y">
                {accounts.data.items.map((account) => (
                  <li
                    key={account.id}
                    className="flex items-center justify-between gap-2 py-2 text-sm"
                  >
                    <Link
                      href={ROUTES.accountDetail(account.id)}
                      className="font-medium hover:underline"
                    >
                      {account.name}
                    </Link>
                    <ProviderBadge provider={account.provider} />
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <EmptyState
              title="No accounts connected"
              message="Connect a cloud account to see costs."
            />
          )}
        </div>
      ) : null}
    </>
  );
}
