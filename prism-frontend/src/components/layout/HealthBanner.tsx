/** PRISM FinOps — platform health warning banner. */

'use client';

import { AlertTriangle } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useHealth } from '@/lib/hooks/useHealth';

export function HealthBanner() {
  const { data } = useHealth();

  if (!data || data.status === 'ok') {
    return null;
  }

  const detail =
    data.status === 'down'
      ? 'Platform services are unavailable. Some data may be stale.'
      : 'Platform performance is degraded. You may see delays.';

  return (
    <Alert variant="destructive" className="rounded-none border-x-0 border-t-0">
      <AlertTriangle className="size-4" />
      <AlertTitle>Platform {data.status}</AlertTitle>
      <AlertDescription>{detail}</AlertDescription>
    </Alert>
  );
}
