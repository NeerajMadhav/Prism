/** PRISM FinOps — connect account entry. */

'use client';

import Link from 'next/link';

import { PageHeader } from '@/components/common/PageHeader';
import { Button } from '@/components/ui/button';
import { ROUTES } from '@/lib/constants/routes';

export default function ConnectAccountPage() {
  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader
        title="Connect Account"
        description="Choose a provider and supply credentials. Full wizard UI expands next."
        actions={
          <Button variant="outline" render={<Link href={ROUTES.accounts} />}>
            Back
          </Button>
        }
      />
      <p className="text-sm text-muted-foreground">
        Use the API-backed connect flow: AWS role ARN, Azure service principal, or GCP service account JSON.
      </p>
    </div>
  );
}
