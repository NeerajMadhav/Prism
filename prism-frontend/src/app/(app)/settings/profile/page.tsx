'use client';

import { PageHeader } from '@/components/common/PageHeader';
import { useAuthStore } from '@/lib/store/authStore';

export default function SettingsProfilePage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="animate-slide-up space-y-4">
      <PageHeader title="Profile" description="Your account details." />
      <div className="rounded-lg border p-4 text-sm">
        <p className="font-medium">{user?.name}</p>
        <p className="text-muted-foreground">{user?.email}</p>
        <p className="mt-2 text-muted-foreground">
          Verified: {user?.email_verified ? 'Yes' : 'No'}
        </p>
      </div>
    </div>
  );
}
