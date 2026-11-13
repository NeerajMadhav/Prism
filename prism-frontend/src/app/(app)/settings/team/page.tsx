'use client';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { PageHeader } from '@/components/common/PageHeader';
import { ROLE_LABELS } from '@/lib/constants/roles';
import { useOrg } from '@/lib/hooks/useOrg';
import { useTeam } from '@/lib/hooks/useTeam';

export default function SettingsTeamPage() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data, isLoading, isError, error, refetch } = useTeam(orgId);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Team" description="Members and roles." />
      {isLoading ? <LoadingSkeleton variant="table" /> : null}
      {isError ? <ErrorState error={error} retry={() => refetch()} /> : null}
      {data && data.items.length === 0 ? (
        <EmptyState title="No members" message="Invite teammates to collaborate." />
      ) : null}
      {data && data.items.length > 0 ? (
        <ul className="divide-y rounded-lg border text-sm">
          {data.items.map((member) => (
            <li key={member.id} className="flex justify-between px-4 py-3">
              <div>
                <p className="font-medium">{member.name}</p>
                <p className="text-muted-foreground">{member.email}</p>
              </div>
              <span className="text-muted-foreground">{ROLE_LABELS[member.role]}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
