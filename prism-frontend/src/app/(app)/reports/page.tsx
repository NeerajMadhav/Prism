/** PRISM FinOps — monthly reports config, HTML preview, PDF download. */

'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { Button } from '@/components/ui/button';
import { useOrg } from '@/lib/hooks/useOrg';
import {
  useDownloadReportPdf,
  useReportPreview,
  useReports,
  useSendReportNow,
} from '@/lib/hooks/useReports';
import { formatCurrency } from '@/lib/utils/currency';

export default function ReportsPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useReports(orgId);
  const preview = useReportPreview(orgId, Boolean(orgId));
  const sendNow = useSendReportNow(orgId);
  const downloadPdf = useDownloadReportPdf(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader
        title="Reports"
        description="Professional monthly HTML reports. Download as PDF or email to stakeholders."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => downloadPdf.mutate()}
              disabled={!orgId || downloadPdf.isPending}
            >
              {downloadPdf.isPending ? 'Preparing PDF…' : 'Download PDF'}
            </Button>
            <Button onClick={() => sendNow.mutate()} disabled={!orgId || sendNow.isPending}>
              {sendNow.isPending ? 'Queuing…' : 'Send now'}
            </Button>
          </div>
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

      {orgId && preview.isLoading ? <LoadingSkeleton variant="card" /> : null}
      {orgId && preview.data ? (
        <div className="space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-semibold">
              Preview — {preview.data.month_label}
            </h2>
            <p className="text-sm text-muted-foreground">
              MTD {formatCurrency(preview.data.total_usd, 'USD')}
            </p>
          </div>
          <div className="overflow-hidden rounded-lg border bg-white">
            <iframe
              title="Monthly report preview"
              className="h-[70vh] w-full bg-white"
              srcDoc={preview.data.html}
              sandbox=""
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
