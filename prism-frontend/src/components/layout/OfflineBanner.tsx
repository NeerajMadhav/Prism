/** PRISM FinOps — offline / WS disconnect banner. */

'use client';

import { WifiOff } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { useWsStore } from '@/lib/store/wsStore';

export function OfflineBanner() {
  const wsUnavailable = useWsStore((s) => s.wsUnavailable);
  const connected = useWsStore((s) => s.connected);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  if (!offline && connected && !wsUnavailable) {
    return null;
  }

  const message = offline
    ? 'You are offline. Cached data is shown until the connection returns.'
    : wsUnavailable
      ? 'Live updates are unavailable. Data may refresh more slowly.'
      : 'Reconnecting to live updates…';

  return (
    <Alert className="rounded-none border-x-0 border-t-0 bg-warning/10 text-foreground">
      <WifiOff className="size-4 text-warning" />
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
