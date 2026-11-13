/** PRISM FinOps — FinOps scorecard hooks. */

import { useQuery } from '@tanstack/react-query';

import * as scorecardApi from '@/lib/api/scorecard';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';

export function useScorecard(orgId: string) {
  return useQuery({
    queryKey: queryKeys.scorecard.detail(orgId),
    queryFn: () => scorecardApi.get(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.scorecard,
  });
}

export function useExecutiveScorecard(orgId: string) {
  return useQuery({
    queryKey: queryKeys.scorecard.executive(orgId),
    queryFn: () => scorecardApi.getExecutive(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.scorecard,
  });
}
