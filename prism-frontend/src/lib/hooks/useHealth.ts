/** PRISM FinOps — backend health polling. */

'use client';

import { useQuery } from '@tanstack/react-query';

import * as healthApi from '@/lib/api/health';
import { qk } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';

export function useHealth() {
  return useQuery({
    queryKey: qk.health(),
    queryFn: () => healthApi.check(),
    staleTime: STALE_TIMES.health,
    refetchInterval: 60_000,
    retry: 1,
  });
}
