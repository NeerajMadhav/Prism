/** PRISM FinOps — budget cap hooks. */

'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as capsApi from '@/lib/api/caps';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { CreateCapRequest, UpdateCapRequest } from '@/types/caps';

export function useCaps(orgId: string) {
  return useQuery({
    queryKey: queryKeys.caps.list(orgId),
    queryFn: () => capsApi.list(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useCap(orgId: string, capId: string) {
  return useQuery({
    queryKey: queryKeys.caps.detail(orgId, capId),
    queryFn: () => capsApi.get(orgId, capId),
    enabled: Boolean(orgId && capId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useCreateCap(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: CreateCapRequest) => capsApi.create(orgId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.caps.all(orgId) });
      toast.success('Budget cap created');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useUpdateCap(orgId: string, capId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: UpdateCapRequest) => capsApi.update(orgId, capId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.caps.all(orgId) });
      toast.success('Budget cap updated');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useRemoveCap(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (capId: string) => capsApi.remove(orgId, capId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.caps.all(orgId) });
      toast.success('Budget cap removed');
    },
    onError: (error) => handleApiError(error),
  });
}
