'use client';

import Link from 'next/link';

import { PageHeader } from '@/components/common/PageHeader';
import { Button } from '@/components/ui/button';
import { ROUTES } from '@/lib/constants/routes';

export default function OnboardingPage() {
  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Onboarding" description="Finish setup to get value from PRISM." />
      <ol className="list-decimal space-y-2 pl-5 text-sm">
        <li>Connect your first cloud billing account</li>
        <li>Set budget caps and notification channels</li>
        <li>Invite teammates to collaborate</li>
      </ol>
      <div className="flex flex-wrap gap-2">
        <Button render={<Link href={ROUTES.accountsConnect} />}>Connect account</Button>
        <Button variant="outline" render={<Link href={ROUTES.settingsNotifications} />}>
          Notification settings
        </Button>
      </div>
    </div>
  );
}
