/** PRISM FinOps — savings recommendation hooks. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as recommendationsApi from '@/lib/api/recommendations';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { RecStatus, RecommendationListParams } from '@/types/recommendations';

export function useRecommendations(orgId: string, params?: RecommendationListParams) {
  return useQuery({
    queryKey: queryKeys.recommendations.list(orgId, params),
    queryFn: () => recommendationsApi.list(orgId, params),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.recommendations,
  });
}

export function useUpdateRecommendationStatus(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      recommendationId,
      status,
    }: {
      recommendationId: string;
      status: RecStatus;
    }) => recommendationsApi.updateStatus(orgId, recommendationId, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recommendations.all(orgId) });
      toast.success('Recommendation updated');
    },
    onError: (error) => handleApiError(error),
  });
}
