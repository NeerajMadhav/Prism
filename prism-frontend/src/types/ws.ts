/** PRISM FinOps — WebSocket event types. */

import type { Provider } from '@/types/api';

export type WsEventType = 'connected' | 'ping' | 'sync.complete';

export interface SyncCompleteData {
  provider: Provider;
  account_id: string;
  account_name: string;
  records: number;
  duration_ms: number;
}

export interface WsEventBase {
  org_id: string;
  timestamp: string;
}

export type WsEvent =
  | (WsEventBase & {
      event: 'connected' | 'ping';
      data: Record<string, unknown>;
    })
  | SyncCompleteEvent;

export interface SyncCompleteEvent extends WsEventBase {
  event: 'sync.complete';
  data: SyncCompleteData;
}
