/** PRISM FinOps — business metric hooks. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as metricsApi from '@/lib/api/metrics';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { CreateMetricRequest, IngestMetricValueRequest } from '@/types/metrics';

export function useMetrics(orgId: string) {
  return useQuery({
    queryKey: queryKeys.metrics.list(orgId),
    queryFn: () => metricsApi.list(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useMetricValues(orgId: string, metricId: string) {
  return useQuery({
    queryKey: queryKeys.metrics.values(orgId, metricId),
    queryFn: () => metricsApi.getValues(orgId, metricId),
    enabled: Boolean(orgId && metricId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useUnitEconomics(orgId: string) {
  return useQuery({
    queryKey: queryKeys.metrics.unitEconomics(orgId),
    queryFn: () => metricsApi.getUnitEconomics(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useCreateMetric(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: CreateMetricRequest) => metricsApi.create(orgId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.metrics.all(orgId) });
      toast.success('Metric created');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useRemoveMetric(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (metricId: string) => metricsApi.remove(orgId, metricId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.metrics.all(orgId) });
      toast.success('Metric removed');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useIngestMetricValue(orgId: string, metricId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: IngestMetricValueRequest) =>
      metricsApi.ingestValue(orgId, metricId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.metrics.values(orgId, metricId),
      });
      toast.success('Value recorded');
    },
    onError: (error) => handleApiError(error),
  });
}
