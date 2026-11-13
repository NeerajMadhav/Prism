/** PRISM FinOps — outbound webhook hooks. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as webhooksApi from '@/lib/api/webhooks';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { CreateWebhookRequest, UpdateWebhookRequest } from '@/types/webhooks';

export function useWebhooks(orgId: string) {
  return useQuery({
    queryKey: queryKeys.webhooks.list(orgId),
    queryFn: () => webhooksApi.list(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useCreateWebhook(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: CreateWebhookRequest) => webhooksApi.create(orgId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.webhooks.all(orgId) });
      toast.success('Webhook created');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useUpdateWebhook(orgId: string, webhookId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: UpdateWebhookRequest) =>
      webhooksApi.update(orgId, webhookId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.webhooks.all(orgId) });
      toast.success('Webhook updated');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useRemoveWebhook(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (webhookId: string) => webhooksApi.remove(orgId, webhookId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.webhooks.all(orgId) });
      toast.success('Webhook removed');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useTestWebhook(orgId: string) {
  return useMutation({
    mutationFn: (webhookId: string) => webhooksApi.test(orgId, webhookId),
    onSuccess: () => toast.success('Test payload sent'),
    onError: (error) => handleApiError(error),
  });
}
