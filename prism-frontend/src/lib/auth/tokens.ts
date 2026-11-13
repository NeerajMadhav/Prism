/** PRISM FinOps — in-memory access token and session refresh storage. */

const REFRESH_KEY = 'prism_rt';
const SESSION_ACTIVE_KEY = 'prism_session_active';

let accessToken: string | null = null;
let proactiveRefreshCleanup: (() => void) | null = null;

type AccessTokenListener = (token: string) => void;
const accessTokenListeners = new Set<AccessTokenListener>();

/** Registers a listener fired when the access token is updated. */
export function onAccessTokenUpdated(listener: AccessTokenListener): () => void {
  accessTokenListeners.add(listener);
  return () => {
    accessTokenListeners.delete(listener);
  };
}

function notifyAccessTokenUpdated(token: string): void {
  accessTokenListeners.forEach((listener) => listener(token));
}

/** Persists tokens after login or refresh. */
export function setTokens(access: string, refresh: string): void {
  accessToken = access;
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.setItem(REFRESH_KEY, refresh);
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(SESSION_ACTIVE_KEY, '1');
  }
  notifyAccessTokenUpdated(access);
}

/** Clears tokens on logout or failed refresh (multi-tab aware). */
export function clearTokens(): void {
  accessToken = null;
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.removeItem(REFRESH_KEY);
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(SESSION_ACTIVE_KEY, '0');
    localStorage.removeItem(SESSION_ACTIVE_KEY);
  }
  proactiveRefreshCleanup?.();
  proactiveRefreshCleanup = null;
}

/** Returns the in-memory access token, if any. */
export function getAccessToken(): string | null {
  return accessToken;
}

/** Returns the refresh token from session storage. */
export function getRefreshToken(): string | null {
  if (typeof sessionStorage === 'undefined') {
    return null;
  }
  return sessionStorage.getItem(REFRESH_KEY);
}

/** Decodes JWT expiry (`exp`) as epoch milliseconds. */
export function decodeTokenExpiry(token: string): number {
  try {
    const payload = token.split('.')[1];
    if (!payload) {
      return 0;
    }
    const json = JSON.parse(atob(payload)) as { exp?: number };
    if (!json.exp) {
      return 0;
    }
    return json.exp * 1000;
  } catch {
    return 0;
  }
}

/** Schedules a proactive refresh two minutes before JWT expiry. */
export function scheduleProactiveRefresh(
  accessTokenValue: string,
  refreshFn: () => void | Promise<void>,
): () => void {
  proactiveRefreshCleanup?.();
  const expMs = decodeTokenExpiry(accessTokenValue);
  if (!expMs) {
    return () => undefined;
  }
  const delay = expMs - 120_000 - Date.now();
  const waitMs = Math.max(delay, 0);
  const timer = setTimeout(() => {
    void refreshFn();
  }, waitMs);
  const cleanup = () => {
    clearTimeout(timer);
  };
  proactiveRefreshCleanup = cleanup;
  return cleanup;
}
