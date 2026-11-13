/** PRISM FinOps — delta and trend formatting. */

export type DeltaDirection = 'up' | 'down' | 'neutral';

/** Formats a percentage delta with optional label suffix. */
export function formatDelta(
  pct: number | null,
  opts?: { label?: string },
): string {
  if (pct === null || Number.isNaN(pct)) {
    return '—';
  }
  const sign = pct > 0 ? '+' : pct < 0 ? '−' : '';
  const value = `${sign}${Math.abs(pct).toFixed(1)}%`;
  if (opts?.label) {
    return `${value} ${opts.label}`;
  }
  return value;
}

/** Returns the direction bucket for a percentage delta. */
export function getDeltaDirection(pct: number): DeltaDirection {
  if (pct > 0) {
    return 'up';
  }
  if (pct < 0) {
    return 'down';
  }
  return 'neutral';
}

/** Returns true when the delta is strictly positive. */
export function isDeltaPositive(pct: number): boolean {
  return pct > 0;
}
