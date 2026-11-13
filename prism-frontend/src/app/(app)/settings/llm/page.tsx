'use client';

import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { useLlmConfig } from '@/lib/hooks/useLlm';
import { useOrg } from '@/lib/hooks/useOrg';

export default function SettingsLlmPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useLlmConfig(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="LLM" description="Assistant provider and budget." />
      {isLoading ? <LoadingSkeleton variant="card" /> : null}
      {isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {data ? (
        <div className="rounded-lg border p-4 text-sm space-y-2">
          <p>
            Status: <strong>{data.configured ? 'Configured' : 'Not configured'}</strong>
          </p>
          {data.provider ? <p>Provider: {data.provider}</p> : null}
          {data.model ? <p>Model: {data.model}</p> : null}
          {typeof data.monthly_budget === 'number' ? (
            <p>Monthly budget: {data.monthly_budget}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
