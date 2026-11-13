/** PRISM FinOps — virtual tag rule hooks. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as virtualTagsApi from '@/lib/api/virtual-tags';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type {
  CreateVirtualTagRuleRequest,
  ReorderVirtualTagRulesRequest,
  UpdateVirtualTagRuleRequest,
} from '@/types/virtual-tags';

export function useVirtualTags(orgId: string) {
  return useQuery({
    queryKey: queryKeys.virtualTags.rules(orgId),
    queryFn: () => virtualTagsApi.list(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useVirtualTagAudit(orgId: string) {
  return useQuery({
    queryKey: queryKeys.virtualTags.audit(orgId),
    queryFn: () => virtualTagsApi.getAuditLog(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useCreateVirtualTag(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: CreateVirtualTagRuleRequest) => virtualTagsApi.create(orgId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.virtualTags.all(orgId) });
      toast.success('Rule created');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useUpdateVirtualTag(orgId: string, ruleId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: UpdateVirtualTagRuleRequest) =>
      virtualTagsApi.update(orgId, ruleId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.virtualTags.all(orgId) });
      toast.success('Rule updated');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useRemoveVirtualTag(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ruleId: string) => virtualTagsApi.remove(orgId, ruleId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.virtualTags.all(orgId) });
      toast.success('Rule removed');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useReorderVirtualTags(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: ReorderVirtualTagRulesRequest) => virtualTagsApi.reorder(orgId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.virtualTags.all(orgId) });
    },
    onError: (error) => handleApiError(error),
  });
}

export function useApplyVirtualTags(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ruleId: string) => virtualTagsApi.apply(orgId, ruleId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.virtualTags.all(orgId) });
      toast.success('Virtual tags applied');
    },
    onError: (error) => handleApiError(error),
  });
}
