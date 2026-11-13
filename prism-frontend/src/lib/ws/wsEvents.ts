/** PRISM FinOps — WebSocket event guards and typed unions. */

import type {
  SyncCompleteData,
  SyncCompleteEvent,
  WsEvent,
  WsEventType,
} from '@/types/ws';

export type { WsEventType, WsEvent, SyncCompleteData, SyncCompleteEvent };

/** Returns true when the event is a sync completion payload. */
export function isSyncCompleteEvent(event: WsEvent): event is SyncCompleteEvent {
  return event.event === 'sync.complete';
}
