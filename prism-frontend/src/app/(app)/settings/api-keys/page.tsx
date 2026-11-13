'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useApiKeys } from '@/lib/hooks/useApiKeys';
import { useOrg } from '@/lib/hooks/useOrg';
import { formatRelative } from '@/lib/utils/dates';

export default function SettingsApiKeysPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useApiKeys(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="API keys" description="Programmatic access tokens." />
      {isLoading ? <LoadingSkeleton variant="table" /> : null}
      {isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {data && data.items.length === 0 ? (
        <EmptyState title="No API keys" message="Create a key for automation." />
      ) : null}
      {data && data.items.length > 0 ? (
        <ul className="divide-y rounded-lg border text-sm">
          {data.items.map((key) => (
            <li key={key.id} className="flex justify-between px-4 py-3">
              <span className="font-medium">{key.name}</span>
              <span className="text-muted-foreground">
                {key.created_at ? formatRelative(key.created_at) : '—'}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
