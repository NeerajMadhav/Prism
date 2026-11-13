/** PRISM FinOps — API error parsing and user feedback. */

import axios from 'axios';
import { toast } from 'sonner';

import type { ApiError, ValidationError } from '@/types/api';

function isValidationErrors(
  detail: ApiError['detail'],
): detail is ValidationError[] {
  return Array.isArray(detail);
}

/** Extracts a human-readable message from an API or network error. */
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | (ApiError & {
          error?: string;
          message?: string;
          details?: Array<{ field?: string; message?: string; msg?: string }>;
        })
      | undefined;
    // Live FastAPI AppError shape: `{ error, code }`
    if (typeof data?.error === 'string' && data.error.length > 0) {
      if (Array.isArray(data.details) && data.details.length > 0) {
        return data.details
          .map((item) => item.message || item.msg || '')
          .filter(Boolean)
          .join(' ') || data.error;
      }
      return data.error;
    }
    if (typeof data?.message === 'string' && data.message.length > 0) {
      return data.message;
    }
    const detail = data?.detail;
    if (typeof detail === 'string' && detail.length > 0) {
      return detail;
    }
    if (detail !== undefined && isValidationErrors(detail) && detail.length > 0) {
      return detail.map((item) => item.msg).join(' ');
    }
    if (error.message) {
      return error.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Something went wrong';
}

/** Shows a toast for a failed mutation or request. */
export function handleApiError(error: unknown, fallback?: string): void {
  if (isAuthError(error)) {
    return;
  }
  toast.error(extractErrorMessage(error) || fallback || 'Something went wrong');
}

/** Returns true when the error is an authentication failure. */
export function isAuthError(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 401;
}

/** Returns true when the error is a rate-limit response. */
export function isRateLimitError(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 429;
}

/** Reads Retry-After from a rate-limit error (defaults to 60 seconds). */
export function getRetryAfterSeconds(error: unknown): number {
  if (!axios.isAxiosError(error)) {
    return 60;
  }
  const header = error.response?.headers?.['retry-after'];
  const parsed = Number.parseInt(String(header ?? ''), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 60;
}
