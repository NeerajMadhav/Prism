/** PRISM FinOps — marks provisional cost data. */

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface EstimatedBadgeProps {
  show?: boolean;
  className?: string;
}

export function EstimatedBadge({ show = true, className }: EstimatedBadgeProps) {
  if (!show) {
    return null;
  }
  return (
    <Badge variant="outline" className={cn('text-warning border-warning/40', className)}>
      Estimated
    </Badge>
  );
}
