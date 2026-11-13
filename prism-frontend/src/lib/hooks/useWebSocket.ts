/** PRISM FinOps — WebSocket connection + cache invalidation. */

'use client';

import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { toast } from 'sonner';

import { getAccessToken, onAccessTokenUpdated } from '@/lib/auth/tokens';
import { clientLogger } from '@/lib/observability/logger';
import { qk } from '@/lib/query/keys';
import { useAuthStore } from '@/lib/store/authStore';
import { useWsStore } from '@/lib/store/wsStore';
import { isSyncCompleteEvent } from '@/lib/ws/wsEvents';
import { wsClient } from '@/lib/ws/wsClient';
import type { SyncCompleteData } from '@/types/ws';

export function useWebSocket() {
  const orgId = useAuthStore((s) => s.org?.id);
  const setConnected = useWsStore((s) => s.setConnected);
  const setLastSync = useWsStore((s) => s.setLastSync);
  const queryClient = useQueryClient();

  useEffect(() => {
    const token = getAccessToken();
    if (!token || !orgId) return;

    wsClient.connect(token);

    const unsubToken = onAccessTokenUpdated((next) => {
      wsClient.updateToken(next);
    });

    const unsub = wsClient.subscribe((event) => {
      if (event.event === 'connected') {
        setConnected(true);
        clientLogger.info('ws_connected', { org_id: orgId });
        return;
      }
      if (isSyncCompleteEvent(event)) {
        const data = event.data as SyncCompleteData;
        setLastSync(data);
        clientLogger.info('sync_complete', {
          org_id: orgId,
          provider: data.provider,
          account_id: data.account_id,
          records: data.records,
        });
        toast.success(
          `✓ ${data.provider} synced · ${data.records.toLocaleString()} records · ${data.account_name ?? data.account_id}`,
        );
        void queryClient.invalidateQueries({ queryKey: qk.costs.all(orgId) });
        void queryClient.invalidateQueries({ queryKey: qk.accounts.all(orgId) });
        void queryClient.invalidateQueries({ queryKey: qk.alerts.all(orgId) });
        void queryClient.invalidateQueries({ queryKey: qk.caps.all(orgId) });
        void queryClient.invalidateQueries({ queryKey: qk.forecasts.all(orgId) });
      }
    });

    return () => {
      unsub();
      unsubToken();
      wsClient.disconnect();
      setConnected(false);
    };
  }, [orgId, queryClient, setConnected, setLastSync]);
}
