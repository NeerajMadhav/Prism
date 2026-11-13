/** PRISM FinOps — LLM assistant config hooks. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as llmApi from '@/lib/api/llm';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { LlmQueryRequest, SetLlmConfigRequest } from '@/types/llm';

export function useLlmConfig(orgId: string) {
  return useQuery({
    queryKey: queryKeys.llm.config(orgId),
    queryFn: () => llmApi.getConfig(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useSetLlmConfig(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: SetLlmConfigRequest) => llmApi.setConfig(orgId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.llm.all(orgId) });
      toast.success('LLM settings saved');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useDeleteLlmConfig(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => llmApi.deleteConfig(orgId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.llm.all(orgId) });
      toast.success('LLM configuration removed');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useLlmQuery(orgId: string) {
  return useMutation({
    mutationFn: (body: LlmQueryRequest) => llmApi.query(orgId, body),
    onError: (error) => handleApiError(error),
  });
}
