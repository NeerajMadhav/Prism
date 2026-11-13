/** PRISM FinOps — authentication hooks. */

'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

import { authApi } from '@/lib/api/auth';
import { refreshAccessToken } from '@/lib/api/client';
import {
  clearTokens,
  getRefreshToken,
  scheduleProactiveRefresh,
  setTokens,
} from '@/lib/auth/tokens';
import { ROUTES } from '@/lib/constants/routes';
import { qk } from '@/lib/query/keys';
import { STALE_TIMES } from '@/lib/query/queryClient';
import { useAuthStore } from '@/lib/store/authStore';
import { handleApiError } from '@/lib/utils/errors';
import { safeRedirectPath } from '@/lib/utils/safeRedirect';
import { wsClient } from '@/lib/ws/wsClient';
import type {
  ChangePasswordRequest,
  LoginRequest,
  ResetPasswordRequest,
  SignupRequest,
  UpdateProfileRequest,
  VerifyEmailRequest,
} from '@/types/auth';

/** Current user session query. */
export function useMe(enabled = true) {
  const setAuth = useAuthStore((s) => s.setAuth);
  return useQuery({
    queryKey: qk.me(),
    queryFn: async () => {
      const me = await authApi.getMe();
      setAuth(me.user, me.org, me.role);
      return me;
    },
    staleTime: STALE_TIMES.me,
    enabled,
    retry: false,
  });
}

/** Email/password login. */
export function useLogin() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: LoginRequest) => authApi.login(body),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      scheduleProactiveRefresh(data.access_token, () => {
        void refreshAccessToken();
      });
      setAuth(data.user, data.org, data.role);
      void queryClient.invalidateQueries({ queryKey: qk.me() });
      const params = new URLSearchParams(window.location.search);
      const from = safeRedirectPath(params.get('from'), ROUTES.dashboard);
      router.replace(from);
    },
    onError: (error) => handleApiError(error, 'Invalid email or password'),
  });
}

/** Logout and clear session. */
export function useLogout() {
  const router = useRouter();
  const clear = useAuthStore((s) => s.clear);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const refresh = getRefreshToken();
      if (refresh) {
        await authApi.logout(refresh);
      }
    },
    onSettled: () => {
      clearTokens();
      clear();
      queryClient.clear();
      wsClient.disconnect(true);
      router.replace(ROUTES.login);
    },
  });
}

/** Signup mutation. */
export function useSignup() {
  return useMutation({
    mutationFn: (body: SignupRequest) => authApi.signup(body),
    onError: (error) => handleApiError(error, 'Could not create account'),
  });
}

/** Verify email token. */
export function useVerifyEmail() {
  const router = useRouter();
  return useMutation({
    mutationFn: (body: VerifyEmailRequest) => authApi.verifyEmail(body),
    onSuccess: () => {
      toast.success('Email verified');
      router.replace(`${ROUTES.login}?verified=1`);
    },
    onError: (error) => handleApiError(error, 'Invalid or expired verification link'),
  });
}

/** Forgot password. */
export function useForgotPassword() {
  return useMutation({
    mutationFn: (email: string) => authApi.forgotPassword(email),
    onSuccess: () => {
      toast.success("If that email exists, we've sent a reset link");
    },
    onError: (error) => handleApiError(error),
  });
}

/** Reset password. */
export function useResetPassword() {
  const router = useRouter();
  return useMutation({
    mutationFn: (body: ResetPasswordRequest) => authApi.resetPassword(body),
    onSuccess: () => {
      toast.success('Password updated');
      router.replace(`${ROUTES.login}?reset=1`);
    },
    onError: (error) => handleApiError(error, 'Reset link expired or invalid'),
  });
}

/** Update authenticated user profile. */
export function useUpdateMe() {
  const queryClient = useQueryClient();
  const setAuth = useAuthStore((s) => s.setAuth);
  const org = useAuthStore((s) => s.org);
  const role = useAuthStore((s) => s.role);

  return useMutation({
    mutationFn: (body: UpdateProfileRequest) => authApi.updateMe(body),
    onSuccess: (user) => {
      if (org && role) {
        setAuth(user, org, role);
      }
      void queryClient.invalidateQueries({ queryKey: qk.me() });
      toast.success('Profile updated');
    },
    onError: (error) => handleApiError(error),
  });
}

/** Change password for the signed-in user. */
export function useChangePassword() {
  return useMutation({
    mutationFn: (body: ChangePasswordRequest) => authApi.changePassword(body),
    onSuccess: (data) => {
      toast.success(data.message || 'Password changed');
    },
    onError: (error) => handleApiError(error),
  });
}

/** Exchange Google OAuth code. */
export function useExchangeOAuth() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);

  return useMutation({
    mutationFn: async ({ code, state }: { code: string; state: string }) => {
      const tokens = await authApi.exchangeOAuthCode({ code, state });
      setTokens(tokens.access_token, tokens.refresh_token);
      const me = await authApi.getMe();
      return { tokens, me };
    },
    onSuccess: ({ me }) => {
      setAuth(me.user, me.org, me.role);
      router.replace(ROUTES.dashboard);
    },
    onError: () => {
      router.replace(`${ROUTES.login}?oauth_error=1`);
    },
  });
}
