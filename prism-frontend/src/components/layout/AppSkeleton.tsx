/** PRISM FinOps — app shell loading placeholder. */

import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface AppSkeletonProps {
  className?: string;
}

/** Sidebar + top bar + content shimmer matching the app shell layout. */
export function AppSkeleton({ className }: AppSkeletonProps) {
  return (
    <div
      className={cn(
        'flex h-screen overflow-hidden opacity-0 animate-in fade-in duration-100 fill-mode-forwards',
        className,
      )}
    >
      <aside className="hidden w-60 shrink-0 bg-gray-900 p-4 lg:block">
        <Skeleton className="mb-8 h-8 w-24 bg-gray-800" />
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full bg-gray-800" />
          ))}
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[60px] items-center gap-4 border-b px-4">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="ml-auto h-8 w-56" />
          <Skeleton className="h-8 w-8 rounded-full" />
        </header>
        <main className="flex-1 space-y-4 p-6">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </main>
      </div>
    </div>
  );
}
