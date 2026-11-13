/** PRISM FinOps — authentication and session types. */

import type { Role } from '@/types/api';

export type { Role };

export interface User {
  id: string;
  name: string;
  email: string;
  avatar_url?: string;
  email_verified: boolean;
  created_at: string;
}

export interface Org {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  feature_flags: Record<string, boolean>;
}

export interface MeResponse {
  user: User;
  org: Org;
  role: Role;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
  org: Org;
  role: Role;
}

export interface SignupRequest {
  name: string;
  email: string;
  password: string;
  org_name: string;
  /** Not accepted by current backend signup — kept optional for UI prefs only. */
  currency?: string;
  timezone?: string;
}

export interface SignupResponse {
  message: string;
  user_id: string;
  org_id: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

export interface VerifyEmailRequest {
  user_id: string;
  token: string;
}

export interface ResendVerificationRequest {
  email: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  user_id: string;
  token: string;
  new_password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface UpdateProfileRequest {
  name?: string;
  avatar_url?: string | null;
}

export interface MessageResponse {
  message: string;
}

export interface OAuthExchangeRequest {
  code: string;
  state: string;
}
