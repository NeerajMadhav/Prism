'use client';

import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useNotifications } from '@/lib/hooks/useNotifications';
import { useOrg } from '@/lib/hooks/useOrg';

export default function SettingsNotificationsPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useNotifications(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Notifications" description="Alert delivery channels and thresholds." />
      {isLoading ? <LoadingSkeleton variant="card" /> : null}
      {isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {data ? (
        <div className="rounded-lg border p-4 text-sm space-y-2">
          <p>
            Email recipients: <strong>{data.alert_emails.join(', ') || 'None'}</strong>
          </p>
          <p>Teams webhook: {data.teams_webhook_url ? 'Configured' : 'Not set'}</p>
          <p>Slack webhook: {data.slack_webhook_url ? 'Configured' : 'Not set'}</p>
        </div>
      ) : null}
    </div>
  );
}
