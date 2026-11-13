/** PRISM FinOps — cloud accounts hooks. */

'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as accountsApi from '@/lib/api/accounts';
import { qk } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { ConnectRequest, SyncStatus } from '@/types/accounts';

export function useAccounts(orgId: string | undefined) {
  return useQuery({
    queryKey: qk.accounts.list(orgId ?? ''),
    queryFn: () => accountsApi.list(orgId!),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.accounts,
  });
}

export function useAccount(orgId: string | undefined, accountId: string | undefined) {
  return useQuery({
    queryKey: qk.accounts.detail(orgId ?? '', accountId ?? ''),
    queryFn: () => accountsApi.get(orgId!, accountId!),
    enabled: Boolean(orgId && accountId),
  });
}

export function useSyncLogs(
  orgId: string | undefined,
  accountId: string | undefined,
  enabled = true,
) {
  return useQuery({
    queryKey: qk.accounts.syncLogs(orgId ?? '', accountId ?? ''),
    queryFn: () => accountsApi.getSyncLogs(orgId!, accountId!),
    enabled: Boolean(orgId && accountId && enabled),
    refetchInterval: (query) => {
      const list = query.state.data?.items ?? [];
      if (!list.length) return 5_000;
      const latest = list[0] as { status?: SyncStatus } | undefined;
      if (latest?.status === 'success' || latest?.status === 'failed') return false;
      return 10_000;
    },
  });
}

export function useConnectAccount(orgId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ConnectRequest) => accountsApi.connect(orgId!, body),
    onSuccess: () => {
      toast.success('Account connected');
      void queryClient.invalidateQueries({ queryKey: qk.accounts.all(orgId!) });
    },
    onError: (error) => handleApiError(error),
  });
}

export function useTriggerSync(orgId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (accountId: string) => accountsApi.sync(orgId!, accountId),
    onSuccess: () => {
      toast.success('Sync started');
      void queryClient.invalidateQueries({ queryKey: qk.accounts.all(orgId!) });
    },
    onError: (error) => handleApiError(error),
  });
}

export function useTestConnection(orgId: string | undefined) {
  return useMutation({
    mutationFn: (accountId: string) => accountsApi.test(orgId!, accountId),
    onError: (error) => handleApiError(error),
  });
}
