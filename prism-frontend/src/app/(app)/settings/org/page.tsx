'use client';

import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useOrg, useOrgDetail } from '@/lib/hooks/useOrg';

export default function SettingsOrgPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const detail = useOrgDetail(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Organization" description="Workspace name, currency, and timezone." />
      {detail.isLoading ? <LoadingSkeleton variant="card" /> : null}
      {detail.isError ? <ErrorState error={detail.error} retry={() => detail.refetch()} /> : null}
      {detail.data ? (
        <div className="rounded-lg border p-4 text-sm space-y-1">
          <p className="font-medium">{detail.data.name}</p>
          <p className="text-muted-foreground">Currency: {detail.data.currency}</p>
          <p className="text-muted-foreground">Timezone: {detail.data.timezone}</p>
        </div>
      ) : null}
    </div>
  );
}
