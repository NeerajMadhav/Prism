/** PRISM FinOps — same-origin relative redirect validation. */

/**
 * Returns a safe in-app path for post-login redirects.
 * Rejects protocol-relative (`//evil.com`), schemes, and backslashes.
 */
export function safeRedirectPath(
  candidate: string | null | undefined,
  fallback: string,
): string {
  if (!candidate) {
    return fallback;
  }
  const path = candidate.trim();
  if (!path.startsWith('/')) {
    return fallback;
  }
  if (path.startsWith('//') || path.startsWith('/\\')) {
    return fallback;
  }
  if (path.includes('://') || path.includes('\\')) {
    return fallback;
  }
  return path;
}
