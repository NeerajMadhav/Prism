/** PRISM FinOps — team and invite types. */

import type { Role } from '@/types/api';

export interface TeamMember {
  id: string;
  user_id: string;
  name: string;
  email: string;
  avatar_url?: string;
  role: Role;
  joined_at: string;
}

export interface Invite {
  id: string;
  email: string;
  role: Role;
  invited_by: string;
  expires_at: string;
}

export interface InviteMemberRequest {
  email: string;
  role: Role;
}

export interface AcceptInviteRequest {
  token: string;
  name?: string;
  password?: string;
}
