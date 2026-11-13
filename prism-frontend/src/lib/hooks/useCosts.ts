/** PRISM FinOps — cost analytics hooks. */

'use client';

import { useQuery } from '@tanstack/react-query';

import * as costsApi from '@/lib/api/costs';
import { qk } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import type { CostQueryParams } from '@/types/costs';

export function useCostSummary(orgId: string | undefined, params?: CostQueryParams) {
  return useQuery({
    queryKey: qk.costs.summary(orgId ?? '', params),
    queryFn: () => costsApi.getSummary(orgId!, params),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.costs,
  });
}

export function useCostsByDay(orgId: string | undefined, params?: CostQueryParams) {
  return useQuery({
    queryKey: qk.costs.byDay(orgId ?? '', params),
    queryFn: () => costsApi.getByDay(orgId!, params),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.costs,
  });
}

export function useCostsByService(orgId: string | undefined, params?: CostQueryParams) {
  return useQuery({
    queryKey: qk.costs.byService(orgId ?? '', params),
    queryFn: () => costsApi.getByService(orgId!, params),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.costs,
  });
}

export function useCostsByTag(
  orgId: string | undefined,
  tagKey: string,
  params?: CostQueryParams,
) {
  return useQuery({
    queryKey: qk.costs.byTag(orgId ?? '', tagKey, params),
    queryFn: () => costsApi.getByTag(orgId!, tagKey, params),
    enabled: Boolean(orgId && tagKey),
    staleTime: STALE_TIMES.costs,
  });
}

export function useTopServices(orgId: string | undefined, params?: CostQueryParams) {
  return useQuery({
    queryKey: qk.costs.topServices(orgId ?? '', params),
    queryFn: () => costsApi.getTopServices(orgId!, params),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.costs,
  });
}
