'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { Button } from '@/components/ui/button';
import { useOrg } from '@/lib/hooks/useOrg';
import { useReports, useSendReportNow } from '@/lib/hooks/useReports';

export default function ReportsPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useReports(orgId);
  const sendNow = useSendReportNow(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader
        title="Reports"
        description="Scheduled executive reporting."
        actions={
          <Button onClick={() => sendNow.mutate()} disabled={!orgId || sendNow.isPending}>
            Send now
          </Button>
        }
      />
      {!orgId ? <EmptyState title="No organization" message="Sign in again." /> : null}
      {orgId && isLoading ? <LoadingSkeleton variant="card" /> : null}
      {orgId && isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {orgId && data ? (
        <div className="space-y-2 rounded-lg border p-4 text-sm">
          <p>
            Status: <strong>{data.is_active ? 'Active' : 'Paused'}</strong>
          </p>
          <p>Recipients: {data.recipient_emails.join(', ') || 'None'}</p>
          <p>Next send: {data.next_send ?? 'Not scheduled'}</p>
        </div>
      ) : null}
    </div>
  );
}
