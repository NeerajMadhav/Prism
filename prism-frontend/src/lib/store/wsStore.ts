/** PRISM FinOps — WebSocket connection state store. */

import { create } from 'zustand';

import type { SyncCompleteData } from '@/types/ws';

interface WsState {
  connected: boolean;
  lastSyncEvent: SyncCompleteData | null;
  wsUnavailable: boolean;
  setConnected: (connected: boolean) => void;
  setLastSync: (data: SyncCompleteData) => void;
  setWsUnavailable: (unavailable: boolean) => void;
}

/** Zustand store for realtime connection metadata. */
export const useWsStore = create<WsState>((set) => ({
  connected: false,
  lastSyncEvent: null,
  wsUnavailable: false,
  setConnected: (connected) => set({ connected }),
  setLastSync: (data) => set({ lastSyncEvent: data }),
  setWsUnavailable: (unavailable) => set({ wsUnavailable: unavailable }),
}));
