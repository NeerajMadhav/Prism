/** PRISM FinOps — month-over-month delta badge. */

import { ArrowDown, ArrowUp, Minus } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { formatDelta, getDeltaDirection } from '@/lib/utils/delta';

interface DeltaBadgeProps {
  pct: number | null;
  invertColors?: boolean;
  className?: string;
}

export function DeltaBadge({ pct, invertColors = false, className }: DeltaBadgeProps) {
  if (pct === null || Number.isNaN(pct)) {
    return (
      <Badge variant="secondary" className={className}>
        —
      </Badge>
    );
  }

  const direction = getDeltaDirection(pct);
  const isGood =
    direction === 'neutral'
      ? true
      : invertColors
        ? direction === 'up'
        : direction === 'down';

  const Icon =
    direction === 'up' ? ArrowUp : direction === 'down' ? ArrowDown : Minus;

  return (
    <Badge
      variant="secondary"
      className={cn(
        'gap-1 font-mono text-xs',
        isGood ? 'text-success' : 'text-destructive',
        className,
      )}
    >
      <Icon className="size-3" aria-hidden />
      {formatDelta(pct)}
    </Badge>
  );
}
