/** PRISM FinOps — notification settings hooks. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as notificationsApi from '@/lib/api/notifications';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { UpdateNotificationSettings } from '@/types/notifications';

export function useNotifications(orgId: string) {
  return useQuery({
    queryKey: queryKeys.notifications(orgId),
    queryFn: () => notificationsApi.get(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useUpdateNotifications(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: UpdateNotificationSettings) =>
      notificationsApi.update(orgId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.notifications(orgId) });
      toast.success('Notification settings saved');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useTestNotificationEmail(orgId: string) {
  return useMutation({
    mutationFn: () => notificationsApi.testEmail(orgId),
    onSuccess: (data) => toast.success(data.message || 'Test email sent'),
    onError: (error) => handleApiError(error),
  });
}

export function useTestNotificationTeams(orgId: string) {
  return useMutation({
    mutationFn: () => notificationsApi.testTeams(orgId),
    onSuccess: (data) => toast.success(data.message || 'Teams test sent'),
    onError: (error) => handleApiError(error),
  });
}

export function useTestNotificationSlack(orgId: string) {
  return useMutation({
    mutationFn: () => notificationsApi.testSlack(orgId),
    onSuccess: (data) => toast.success(data.message || 'Slack test sent'),
    onError: (error) => handleApiError(error),
  });
}
