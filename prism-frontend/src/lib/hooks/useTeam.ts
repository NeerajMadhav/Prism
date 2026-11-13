/** PRISM FinOps — team membership hooks. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as teamApi from '@/lib/api/team';
import { queryKeys } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { handleApiError } from '@/lib/utils/errors';
import type { Role } from '@/types/api';
import type { AcceptInviteRequest, InviteMemberRequest } from '@/types/team';

export function useTeam(orgId: string) {
  return useQuery({
    queryKey: queryKeys.team.members(orgId),
    queryFn: () => teamApi.listMembers(orgId),
    enabled: Boolean(orgId),
    staleTime: STALE_TIMES.settings,
  });
}

export function useInviteMember(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: InviteMemberRequest) => teamApi.inviteMember(orgId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.team.all(orgId) });
      toast.success('Invitation sent');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useAcceptInvite(orgId: string) {
  return useMutation({
    mutationFn: (body: AcceptInviteRequest) => teamApi.acceptInvite(orgId, body),
    onSuccess: () => toast.success('Invitation accepted'),
    onError: (error) => handleApiError(error),
  });
}

export function useChangeMemberRole(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: Role }) =>
      teamApi.changeRole(orgId, memberId, role),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.team.all(orgId) });
      toast.success('Role updated');
    },
    onError: (error) => handleApiError(error),
  });
}

export function useRemoveMember(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (memberId: string) => teamApi.removeMember(orgId, memberId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.team.all(orgId) });
      toast.success('Member removed');
    },
    onError: (error) => handleApiError(error),
  });
}
