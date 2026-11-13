/** PRISM FinOps — organization hooks. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as orgApi from '@/lib/api/org';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { useAuthStore } from '@/lib/store/authStore';
import { handleApiError } from '@/lib/utils/errors';
import type { UpdateOrgRequest } from '@/types/org';

/** Returns the organization from the auth store (hydrated via `useMe`). */
export function useOrg() {
  return useAuthStore((s) => s.org);
}

/** Fetches full organization details from the API. */
export function useOrgDetail(orgId: string | undefined) {
  return useQuery({
    queryKey: orgId ? queryKeys.org(orgId) : ['prism', 'org', 'none'],
    queryFn: () => orgApi.getOrg(orgId!),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

/** Updates organization settings and refreshes org + me queries. */
export function useUpdateOrg(orgId: string) {
  const queryClient = useQueryClient();
  const setAuth = useAuthStore((s) => s.setAuth);
  const user = useAuthStore((s) => s.user);
  const role = useAuthStore((s) => s.role);

  return useMutation({
    mutationFn: (body: UpdateOrgRequest) => orgApi.updateOrg(orgId, body),
    onSuccess: (org) => {
      if (user && role) {
        setAuth(user, {
          id: org.id,
          name: org.name,
          currency: org.currency,
          timezone: org.timezone,
          feature_flags: Object.fromEntries(
            Object.entries(org.feature_flags).map(([k, v]) => [k, Boolean(v)]),
          ),
        }, role);
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.org(orgId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.me() });
      toast.success('Organization updated');
    },
    onError: (error) => handleApiError(error),
  });
}
