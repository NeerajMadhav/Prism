/** PRISM FinOps — commitment hooks. */

import { useQuery } from '@tanstack/react-query';

import * as commitmentsApi from '@/lib/api/commitments';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';

export function useCommitments(orgId: string) {
  return useQuery({
    queryKey: queryKeys.commitments.list(orgId),
    queryFn: () => commitmentsApi.list(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useCommitmentSummary(orgId: string) {
  return useQuery({
    queryKey: queryKeys.commitments.summary(orgId),
    queryFn: () => commitmentsApi.getSummary(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useExpiringCommitments(orgId: string) {
  return useQuery({
    queryKey: queryKeys.commitments.expiring(orgId),
    queryFn: () => commitmentsApi.getExpiring(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}
