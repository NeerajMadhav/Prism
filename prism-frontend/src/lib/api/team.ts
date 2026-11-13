/** PRISM FinOps — team management API (normalized to UI types). */

import { apiClient } from '@/lib/api/client';
import { normalizePaginated } from '@/lib/api/normalize';
import type { Paginated, Role } from '@/types/api';
import type {
  AcceptInviteRequest,
  InviteMemberRequest,
  TeamMember,
} from '@/types/team';
import type { MessageResponse } from '@/types/auth';

interface BackendTeamMember {
  id: string;
  user_id: string;
  email: string;
  name: string;
  role: Role;
  invite_accepted?: boolean;
  created_at: string;
}

/** Maps backend team member rows into UI `TeamMember`. */
export function normalizeTeamMember(row: BackendTeamMember): TeamMember {
  return {
    id: row.id,
    user_id: row.user_id,
    email: row.email,
    name: row.name,
    role: row.role,
    joined_at: row.created_at,
  };
}

/** Lists team members for an organization. */
export async function listMembers(orgId: string): Promise<Paginated<TeamMember>> {
  const { data } = await apiClient.get<BackendTeamMember[] | Paginated<BackendTeamMember>>(
    `/orgs/${orgId}/team`,
  );
  const page = normalizePaginated(data);
  return { ...page, items: page.items.map(normalizeTeamMember) };
}

/** Sends a team invite email. */
export async function inviteMember(
  orgId: string,
  body: InviteMemberRequest,
): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(
    `/orgs/${orgId}/team/invite`,
    body,
  );
  return data;
}

/** Accepts a pending team invite. */
export async function acceptInvite(
  orgId: string,
  body: AcceptInviteRequest,
): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(
    `/orgs/${orgId}/team/accept-invite`,
    body,
  );
  return data;
}

/** Updates a member's role. */
export async function changeRole(
  orgId: string,
  memberId: string,
  role: Role,
): Promise<TeamMember> {
  const { data } = await apiClient.put<BackendTeamMember>(
    `/orgs/${orgId}/team/${memberId}/role`,
    { role },
  );
  return normalizeTeamMember(data);
}

/** Removes a member from the organization. */
export async function removeMember(
  orgId: string,
  memberId: string,
): Promise<void> {
  await apiClient.delete(`/orgs/${orgId}/team/${memberId}`);
}
