/** PRISM FinOps — forecast hooks. */

import { useQuery } from '@tanstack/react-query';

import * as forecastsApi from '@/lib/api/forecasts';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';

export function useForecasts(orgId: string) {
  return useQuery({
    queryKey: queryKeys.forecasts.current(orgId),
    queryFn: () => forecastsApi.getCurrent(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.forecasts,
  });
}

export function useForecastHistory(orgId: string) {
  return useQuery({
    queryKey: queryKeys.forecasts.history(orgId),
    queryFn: () => forecastsApi.getHistory(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.forecasts,
  });
}
