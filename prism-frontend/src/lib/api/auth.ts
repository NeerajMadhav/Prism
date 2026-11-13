/** PRISM FinOps — authentication API module. */

import { apiClient } from '@/lib/api/client';
import type { Role } from '@/types/api';
import type {
  ChangePasswordRequest,
  LoginRequest,
  LoginResponse,
  MeResponse,
  MessageResponse,
  OAuthExchangeRequest,
  Org,
  ResetPasswordRequest,
  ResendVerificationRequest,
  SignupRequest,
  SignupResponse,
  TokenResponse,
  UpdateProfileRequest,
  User,
  VerifyEmailRequest,
} from '@/types/auth';
import type { OrgDetail } from '@/types/org';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface FlatMeResponse {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  org_id: string;
  org_name?: string;
  role: Role;
  email_verified: boolean;
  last_login?: string;
}

interface BackendLoginResponse extends TokenResponse {
  user?: {
    id: string;
    email: string;
    name: string;
    org_id: string;
    role: Role;
  };
}

/** Normalizes flat `/auth/me` payloads into `MeResponse`. */
function normalizeMe(data: MeResponse | FlatMeResponse): MeResponse {
  if ('user' in data && data.user) {
    return data;
  }
  const flat = data as FlatMeResponse;
  const user: User = {
    id: flat.id,
    email: flat.email,
    name: flat.name,
    avatar_url: flat.avatar_url,
    email_verified: flat.email_verified,
    created_at: flat.last_login ?? new Date().toISOString(),
  };
  const org: Org = {
    id: flat.org_id,
    name: flat.org_name ?? 'Organization',
    currency: 'USD',
    timezone: 'UTC',
    feature_flags: {},
  };
  return { user, org, role: flat.role };
}

/** Creates a user and organization. */
export async function signup(body: SignupRequest): Promise<SignupResponse> {
  // Backend SignupRequest only accepts email/name/password/org_name.
  const { data } = await apiClient.post<SignupResponse>('/auth/signup', {
    email: body.email,
    name: body.name,
    password: body.password,
    org_name: body.org_name,
  });
  return data;
}

/** Confirms email verification token. */
export async function verifyEmail(body: VerifyEmailRequest): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/auth/verify-email', body);
  return data;
}

/** Resends the email verification link. */
export async function resendVerification(
  body: ResendVerificationRequest,
): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(
    '/auth/resend-verification',
    body,
  );
  return data;
}

/** Authenticates with email and password. */
export async function login(body: LoginRequest): Promise<LoginResponse> {
  const { data } = await apiClient.post<BackendLoginResponse>('/auth/login', body);
  if (data.user) {
    const org: Org = {
      id: data.user.org_id,
      name: 'Organization',
      currency: 'USD',
      timezone: 'UTC',
      feature_flags: {},
    };
    const user: User = {
      id: data.user.id,
      email: data.user.email,
      name: data.user.name,
      email_verified: true,
      created_at: new Date().toISOString(),
    };
    return {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      user,
      org,
      role: data.user.role,
    };
  }
  const me = await getMe();
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    user: me.user,
    org: me.org,
    role: me.role,
  };
}

/** Rotates access and refresh tokens. */
export async function refresh(refreshToken: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  });
  return data;
}

/** Revokes the refresh token. */
export async function logout(refreshToken: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/auth/logout', {
    refresh_token: refreshToken,
  });
  return data;
}

/** Returns the current user, organization, and role. */
export async function getMe(): Promise<MeResponse> {
  const { data } = await apiClient.get<MeResponse | FlatMeResponse>('/auth/me');
  return normalizeMe(data);
}

/** Updates the authenticated user's profile. */
export async function updateMe(body: UpdateProfileRequest): Promise<User> {
  const { data } = await apiClient.put<User>('/auth/me', body);
  return data;
}

/** Changes password for the authenticated user. */
export async function changePassword(
  body: ChangePasswordRequest,
): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>(
    '/auth/change-password',
    body,
  );
  return data;
}

/** Sends a password reset email. */
export async function forgotPassword(email: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/auth/forgot-password', {
    email,
  });
  return data;
}

/** Resets password using a reset token. */
export async function resetPassword(
  body: ResetPasswordRequest,
): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/auth/reset-password', body);
  return data;
}

/** Returns the Google OAuth URL (optionally redirects the browser). */
export function startGoogleOAuth(redirect = false): string {
  const url = `${API_BASE}/v1/auth/google`;
  if (redirect && typeof window !== 'undefined') {
    // External IdP URL (backend), not an in-app Next.js route.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- leaves the app for Google OAuth
    window.location.href = url;
  }
  return url;
}

/** Exchanges an OAuth code for tokens. */
export async function exchangeOAuthCode(
  body: OAuthExchangeRequest,
): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/oauth/exchange', body);
  return data;
}

/** Fetches full organization details to enrich auth org context. */
export async function fetchOrgForMe(orgId: string): Promise<OrgDetail> {
  const { data } = await apiClient.get<OrgDetail>(`/orgs/${orgId}`);
  return data;
}

/** Namespaced auth API for convenient imports. */
export const authApi = {
  signup,
  verifyEmail,
  resendVerification,
  login,
  refresh,
  logout,
  getMe,
  updateMe,
  changePassword,
  forgotPassword,
  resetPassword,
  startGoogleOAuth,
  exchangeOAuthCode,
  fetchOrgForMe,
};
