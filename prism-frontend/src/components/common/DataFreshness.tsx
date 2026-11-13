/** PRISM FinOps — last-synced timestamp label. */

import { formatDistanceToNow } from 'date-fns';

import { cn } from '@/lib/utils';

interface DataFreshnessProps {
  dataAsOf: string | null | undefined;
  className?: string;
}

export function DataFreshness({ dataAsOf, className }: DataFreshnessProps) {
  if (!dataAsOf) {
    return (
      <p className={cn('text-xs text-muted-foreground', className)}>Data freshness unknown</p>
    );
  }

  const relative = formatDistanceToNow(new Date(dataAsOf), { addSuffix: true });

  return (
    <p className={cn('text-xs text-muted-foreground', className)}>Updated {relative}</p>
  );
}
