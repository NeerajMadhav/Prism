/** PRISM FinOps — URL helpers for FastAPI slash-sensitive routes. */

/**
 * FastAPI routes registered as `@router.get("/")` 307-redirect bare paths to a
 * trailing slash. Some HTTP stacks strip Authorization on that hop → spurious 401.
 */
const TRAILING_SLASH_COLLECTIONS = [
  '/caps',
  '/alerts',
  '/forecasts',
  '/metrics',
  '/virtual-tags',
  '/scorecard',
  '/recommendations',
  '/commitments',
  '/resources',
  '/webhooks',
  '/api-keys',
  '/reports',
  '/notifications',
  '/llm',
] as const;

/** Appends `/` to known FastAPI collection roots when missing. */
export function ensureTrailingSlashPath(url: string): string {
  const qIndex = url.indexOf('?');
  const path = qIndex >= 0 ? url.slice(0, qIndex) : url;
  const query = qIndex >= 0 ? url.slice(qIndex) : '';
  if (path.endsWith('/')) return url;
  const needsSlash = TRAILING_SLASH_COLLECTIONS.some((suffix) => path.endsWith(suffix));
  return needsSlash ? `${path}/${query}` : url;
}
