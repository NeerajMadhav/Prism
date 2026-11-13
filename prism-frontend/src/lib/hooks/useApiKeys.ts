/** PRISM FinOps — API key hooks. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as apiKeysApi from '@/lib/api/api-keys';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { CreateApiKeyRequest } from '@/types/api-keys';

export function useApiKeys(orgId: string) {
  return useQuery({
    queryKey: queryKeys.apiKeys.list(orgId),
    queryFn: () => apiKeysApi.list(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useCreateApiKey(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: CreateApiKeyRequest) => apiKeysApi.create(orgId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys.all(orgId) });
      toast.success('API key created — copy it now');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useRevokeApiKey(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (keyId: string) => apiKeysApi.revoke(orgId, keyId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys.all(orgId) });
      toast.success('API key revoked');
    },
    onError: (error) => handleApiError(error),
  });
}
