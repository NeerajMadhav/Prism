/** PRISM FinOps — cloud resource hooks. */

import { useQuery } from '@tanstack/react-query';

import * as resourcesApi from '@/lib/api/resources';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import type { ResourceListParams } from '@/types/resources';

export function useResources(orgId: string, params?: ResourceListParams) {
  return useQuery({
    queryKey: queryKeys.resources.list(orgId, params),
    queryFn: () => resourcesApi.list(orgId, params),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useIdleResources(orgId: string) {
  return useQuery({
    queryKey: queryKeys.resources.idle(orgId),
    queryFn: () => resourcesApi.listIdle(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useResource(orgId: string, resourceId: string) {
  return useQuery({
    queryKey: queryKeys.resources.detail(orgId, resourceId),
    queryFn: () => resourcesApi.get(orgId, resourceId),
    enabled: Boolean(orgId && resourceId),
    staleTime: STALE_TIMES.settings,
  });
}
