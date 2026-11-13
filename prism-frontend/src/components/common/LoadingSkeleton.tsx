/** PRISM FinOps — layout-matched loading placeholders. */

import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

export type LoadingSkeletonVariant = 'card' | 'table' | 'kpi-row' | 'chart';

interface LoadingSkeletonProps {
  variant?: LoadingSkeletonVariant;
  className?: string;
}

/** Shimmer skeletons aligned to common page shapes. */
export function LoadingSkeleton({
  variant = 'card',
  className,
}: LoadingSkeletonProps) {
  if (variant === 'table') {
    return (
      <div className={cn('space-y-2 rounded-lg border p-4', className)}>
        <Skeleton className="h-8 w-full" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (variant === 'kpi-row') {
    return (
      <div className={cn('grid gap-4 sm:grid-cols-2 lg:grid-cols-4', className)}>
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (variant === 'chart') {
    return <Skeleton className={cn('h-64 w-full rounded-xl', className)} />;
  }

  return <Skeleton className={cn('h-32 w-full rounded-xl', className)} />;
}
