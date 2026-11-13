/** PRISM FinOps — active alerts slide-over panel. */

'use client';

import Link from 'next/link';
import { Bell } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { ROUTES } from '@/lib/constants/routes';
import { useAcknowledge, useAlerts, useAlertsCount } from '@/lib/hooks/useAlerts';
import { useOrg } from '@/lib/hooks/useOrg';
import { formatRelative } from '@/lib/utils/dates';

/** Bell trigger + sheet listing recent active alerts. */
export function NotificationsPanel() {
  const org = useOrg();
  const orgId = org?.id ?? '';
  const { data: countData } = useAlertsCount(orgId);
  const activeCount = countData?.active ?? 0;
  const { data, isLoading } = useAlerts(orgId, { status: 'active', size: 10 });
  const acknowledge = useAcknowledge(orgId);

  return (
    <Sheet>
      <SheetTrigger
        render={
          <Button variant="outline" size="sm" className="relative gap-2" aria-label="Notifications">
            <Bell className="size-4" />
            {activeCount > 0 ? (
              <span className="rounded-full bg-destructive px-1.5 text-xs text-white">
                {activeCount > 99 ? '99+' : activeCount}
              </span>
            ) : null}
          </Button>
        }
      />
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Notifications</SheetTitle>
          <SheetDescription>Recent active alerts</SheetDescription>
        </SheetHeader>
        <div className="mt-4 space-y-3">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : !data?.items.length ? (
            <p className="text-sm text-muted-foreground">No active alerts</p>
          ) : (
            data.items.map((alert) => (
              <div key={alert.id} className="rounded-lg border p-3 text-sm">
                <p className="font-medium capitalize">{alert.type.replaceAll('_', ' ')}</p>
                <p className="text-xs text-muted-foreground">
                  {formatRelative(alert.triggered_at)}
                </p>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="mt-2"
                  disabled={acknowledge.isPending}
                  onClick={() => acknowledge.mutate(alert.id)}
                >
                  Acknowledge
                </Button>
              </div>
            ))
          )}
        </div>
        <Button variant="secondary" className="mt-6 w-full" render={<Link href={ROUTES.alerts} />}>
          View all alerts
        </Button>
      </SheetContent>
    </Sheet>
  );
}
