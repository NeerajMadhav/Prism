/** PRISM FinOps — alerts hooks. */

'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as alertsApi from '@/lib/api/alerts';
import { qk } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { AlertListParams } from '@/types/alerts';

export function useAlerts(orgId: string | undefined, params?: AlertListParams) {
  return useQuery({
    queryKey: qk.alerts.list(orgId ?? '', params),
    queryFn: () => alertsApi.list(orgId!, params),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.alerts,
  });
}

export function useAlertsCount(orgId: string | undefined) {
  return useQuery({
    queryKey: qk.alerts.count(orgId ?? ''),
    queryFn: () => alertsApi.count(orgId!),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.alerts,
    refetchInterval: 60_000,
  });
}

export function useAcknowledge(orgId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => alertsApi.acknowledge(orgId!, alertId),
    onSuccess: () => {
      toast.success('Alert acknowledged');
      void queryClient.invalidateQueries({ queryKey: qk.alerts.all(orgId!) });
    },
    onError: (error) => handleApiError(error),
  });
}

export function useSnooze(orgId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, until }: { alertId: string; until: string }) =>
      alertsApi.snooze(orgId!, alertId, { until }),
    onSuccess: () => {
      toast.success('Alert snoozed');
      void queryClient.invalidateQueries({ queryKey: qk.alerts.all(orgId!) });
    },
    onError: (error) => handleApiError(error),
  });
}
