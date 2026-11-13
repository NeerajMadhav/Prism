/** PRISM FinOps — TanStack Query client defaults. */

import { QueryClient } from '@tanstack/react-query';

/** Shared query client with domain stale times and resilient networking. */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Serve cache immediately, revalidate in background under load / tab focus.
        networkMode: 'offlineFirst',
        staleTime: 60_000,
        gcTime: 15 * 60_000,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
        refetchOnMount: true,
        retry: (failureCount, error) => {
          const status = (error as { response?: { status?: number } })?.response?.status;
          if (status === 401 || status === 403 || status === 404 || status === 429) {
            return false;
          }
          return failureCount < 2;
        },
      },
      mutations: {
        networkMode: 'online',
        retry: 0,
      },
    },
  });
}

export const STALE_TIMES = {
  me: 10 * 60_000,
  health: 60_000,
  costs: 5 * 60_000,
  accounts: 60_000,
  alerts: 60_000,
  settings: 10 * 60_000,
  forecasts: 5 * 60_000,
  scorecard: 10 * 60_000,
  recommendations: 5 * 60_000,
} as const;

export const queryClient = createQueryClient();
