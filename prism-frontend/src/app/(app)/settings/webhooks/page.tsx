'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useOrg } from '@/lib/hooks/useOrg';
import { useWebhooks } from '@/lib/hooks/useWebhooks';

export default function SettingsWebhooksPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useWebhooks(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Webhooks" description="Outbound event integrations." />
      {isLoading ? <LoadingSkeleton variant="table" /> : null}
      {isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {data && data.items.length === 0 ? (
        <EmptyState title="No webhooks" message="Create a webhook to push events." />
      ) : null}
      {data && data.items.length > 0 ? (
        <ul className="divide-y rounded-lg border text-sm">
          {data.items.map((hook) => (
            <li key={hook.id} className="px-4 py-3">
              <p className="font-medium">{hook.url}</p>
              <p className="text-muted-foreground truncate">{hook.events.join(', ')}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
