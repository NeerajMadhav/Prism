/** PRISM FinOps — singleton WebSocket client with reconnect and ping. */

import { clientLogger } from '@/lib/observability/logger';
import { useWsStore } from '@/lib/store/wsStore';
import { encodeWsAuthProtocol } from '@/lib/ws/wsToken';
import type { WsEvent } from '@/types/ws';

type WsListener = (event: WsEvent) => void;

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL ??
  process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, 'ws') ??
  'ws://localhost:8000';

const MAX_RECONNECT_DELAY_MS = 30_000;
const PING_INTERVAL_MS = 25_000;
const CONNECTION_CEILING_MS = 55 * 60_000;
const MAX_FAILED_ATTEMPTS = 3;

class WsClient {
  private socket: WebSocket | null = null;
  private token: string | null = null;
  private listeners = new Set<WsListener>();
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private ceilingTimer: ReturnType<typeof setTimeout> | null = null;
  private paused = false;
  private manuallyClosed = false;
  private refCount = 0;
  private visibilityBound = false;

  /** Opens the WebSocket when not already connected. */
  connect(token: string): void {
    if (typeof window === 'undefined') {
      return;
    }
    this.refCount += 1;
    this.token = token;
    this.manuallyClosed = false;
    if (
      this.socket?.readyState === WebSocket.OPEN ||
      this.socket?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }
    this.openSocket(token);
    this.bindVisibilityHandler();
  }

  /** Applies a refreshed access token; reconnects only when it changes. */
  updateToken(newToken: string): void {
    if (!newToken) {
      return;
    }
    if (this.token === newToken && this.socket?.readyState === WebSocket.OPEN) {
      return;
    }
    this.token = newToken;
    if (this.refCount <= 0 || this.manuallyClosed) {
      return;
    }
    this.closeSocket();
    this.scheduleReconnect(0);
  }

  /** Registers an event listener; returns an unsubscribe function. */
  subscribe(listener: WsListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /** Releases one subscriber; `force` tears down on logout. */
  disconnect(force = false): void {
    this.refCount = force ? 0 : Math.max(0, this.refCount - 1);
    if (this.refCount > 0) {
      return;
    }
    this.manuallyClosed = true;
    this.clearTimers();
    this.closeSocket();
    useWsStore.getState().setConnected(false);
  }

  private openSocket(token: string): void {
    this.clearReconnectTimer();
    // Auth via Sec-WebSocket-Protocol — never put JWT in the query string (logs/Referer).
    const url = `${WS_BASE.replace(/\/$/, '')}/ws`;
    const protocol = encodeWsAuthProtocol(token);
    this.socket = new WebSocket(url, [protocol]);

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      useWsStore.getState().setConnected(true);
      useWsStore.getState().setWsUnavailable(false);
      clientLogger.info('ws_open');
      this.startPing();
      this.startCeilingTimer();
    };

    this.socket.onmessage = (message) => {
      try {
        const event = JSON.parse(String(message.data)) as WsEvent;
        if (event.event === 'ping') {
          return;
        }
        this.listeners.forEach((listener) => listener(event));
      } catch {
        // Drop malformed frames without tearing down the socket.
      }
    };

    this.socket.onerror = () => {
      clientLogger.warn('ws_error');
      this.socket?.close();
    };

    this.socket.onclose = () => {
      useWsStore.getState().setConnected(false);
      this.stopPing();
      clientLogger.info('ws_close', {
        manual: this.manuallyClosed,
        attempt: this.reconnectAttempts,
      });
      if (!this.manuallyClosed && this.refCount > 0) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(delayOverride?: number): void {
    if (this.manuallyClosed || !this.token || this.refCount <= 0) {
      return;
    }
    if (this.reconnectTimer) {
      return;
    }
    this.reconnectAttempts += 1;
    if (this.reconnectAttempts > MAX_FAILED_ATTEMPTS) {
      useWsStore.getState().setWsUnavailable(true);
    }
    const delay =
      delayOverride ??
      Math.min(1000 * 2 ** (this.reconnectAttempts - 1), MAX_RECONNECT_DELAY_MS);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (this.token && this.refCount > 0 && !this.manuallyClosed) {
        this.openSocket(this.token);
      }
    }, delay);
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      if (this.paused) {
        return;
      }
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'ping' }));
      }
    }, PING_INTERVAL_MS);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private startCeilingTimer(): void {
    this.clearCeilingTimer();
    this.ceilingTimer = setTimeout(() => {
      if (this.token) {
        this.closeSocket();
        this.scheduleReconnect(0);
      }
    }, CONNECTION_CEILING_MS);
  }

  private clearCeilingTimer(): void {
    if (this.ceilingTimer) {
      clearTimeout(this.ceilingTimer);
      this.ceilingTimer = null;
    }
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private clearTimers(): void {
    this.stopPing();
    this.clearReconnectTimer();
    this.clearCeilingTimer();
  }

  private closeSocket(): void {
    if (this.socket) {
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onerror = null;
      this.socket.onclose = null;
      this.socket.close();
      this.socket = null;
    }
  }

  private bindVisibilityHandler(): void {
    if (typeof document === 'undefined' || this.visibilityBound) {
      return;
    }
    this.visibilityBound = true;
    document.addEventListener('visibilitychange', () => {
      this.paused = document.visibilityState === 'hidden';
      if (
        document.visibilityState === 'visible' &&
        this.token &&
        this.refCount > 0 &&
        (!this.socket || this.socket.readyState !== WebSocket.OPEN)
      ) {
        this.scheduleReconnect(0);
      }
    });
  }
}

export const wsClient = new WsClient();
