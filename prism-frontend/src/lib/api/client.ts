/** PRISM FinOps — Axios HTTP client with auth refresh and rate-limit handling. */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios';
import { toast } from 'sonner';

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  scheduleProactiveRefresh,
  setTokens,
} from '@/lib/auth/tokens';
import { ensureTrailingSlashPath } from '@/lib/api/paths';
import {
  clientLogger,
  createClientRequestId,
} from '@/lib/observability/logger';
import { useAuthStore } from '@/lib/store/authStore';
import { getRetryAfterSeconds, isRateLimitError } from '@/lib/utils/errors';
import { safeRedirectPath } from '@/lib/utils/safeRedirect';
import type { TokenResponse } from '@/types/auth';

interface RetryableRequest extends InternalAxiosRequestConfig {
  _retry?: boolean;
  _rateLimitRetry?: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

/** Single-flight refresh — backend rotates refresh tokens atomically; parallel refresh = logout. */
let refreshInFlight: Promise<string> | null = null;

const failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function flushQueue(error: unknown, token: string | null): void {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error || !token) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  failedQueue.length = 0;
}

function redirectToLogin(): void {
  clearTokens();
  useAuthStore.getState().clear();
  if (typeof window !== 'undefined') {
    const from = safeRedirectPath(
      window.location.pathname + window.location.search,
      '/',
    );
    const login = `/login?from=${encodeURIComponent(from)}`;
    // Hard navigation clears in-memory auth state after failed refresh (not a soft client route).
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- full reload required
    window.location.href = login;
  }
}

/** Performs a silent refresh once; concurrent callers share the same promise. */
export async function refreshAccessToken(): Promise<string> {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token');
    }
    const { data } = await axios.post<TokenResponse>(
      `${API_BASE}/v1/auth/refresh`,
      { refresh_token: refreshToken },
      { headers: { 'Content-Type': 'application/json' } },
    );
    setTokens(data.access_token, data.refresh_token);
    scheduleProactiveRefresh(data.access_token, () => {
      void refreshAccessToken().catch(() => {
        redirectToLogin();
      });
    });
    return data.access_token;
  })().finally(() => {
    refreshInFlight = null;
  });

  return refreshInFlight;
}

function isAuthCredentialRequest(url: string | undefined): boolean {
  if (!url) return false;
  return (
    url.includes('/auth/login') ||
    url.includes('/auth/refresh') ||
    url.includes('/auth/signup') ||
    url.includes('/auth/oauth')
  );
}

/** Shared Axios instance for authenticated API calls. */
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE}/v1`,
  timeout: 30_000,
  maxRedirects: 0,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (typeof config.url === 'string') {
    config.url = ensureTrailingSlashPath(config.url);
  }
  if (!config.headers['X-Request-Id'] && !config.headers['x-request-id']) {
    config.headers['X-Request-Id'] = createClientRequestId();
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryableRequest | undefined;
    if (!original) {
      return Promise.reject(error);
    }

    const status = error.response?.status;
    const requestId =
      (error.response?.headers?.['x-request-id'] as string | undefined) ||
      String(original.headers?.['X-Request-Id'] ?? '');
    if (status && status >= 400 && status !== 401) {
      clientLogger.warn('api_error', {
        status,
        method: String(original.method ?? 'get').toUpperCase(),
        path: String(original.url ?? ''),
        request_id: requestId || null,
      });
    }

    if (
      error.response?.status === 401 &&
      !original._retry &&
      !isAuthCredentialRequest(original.url)
    ) {
      original._retry = true;

      if (refreshInFlight) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token) => {
              original.headers.Authorization = `Bearer ${token}`;
              resolve(apiClient(original));
            },
            reject,
          });
        });
      }

      try {
        const token = await refreshAccessToken()
          .then((next) => {
            flushQueue(null, next);
            return next;
          })
          .catch((refreshError) => {
            flushQueue(refreshError, null);
            redirectToLogin();
            throw refreshError;
          });
        original.headers.Authorization = `Bearer ${token}`;
        return apiClient(original);
      } catch (refreshError) {
        return Promise.reject(refreshError);
      }
    }

    if (isRateLimitError(error) && !original._rateLimitRetry) {
      original._rateLimitRetry = true;
      const waitSeconds = getRetryAfterSeconds(error);
      await new Promise((resolve) => setTimeout(resolve, waitSeconds * 1000));
      try {
        return await apiClient(original);
      } catch (retryError) {
        if (isRateLimitError(retryError)) {
          toast.error(`Rate limit reached. Try again in ${waitSeconds}s.`);
        }
        return Promise.reject(retryError);
      }
    }

    return Promise.reject(error);
  },
);
