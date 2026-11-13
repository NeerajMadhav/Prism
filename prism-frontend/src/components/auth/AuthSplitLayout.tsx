/** PRISM FinOps — marketing + form split auth layout. */

import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

interface AuthSplitLayoutProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}

export function AuthSplitLayout({ title, subtitle, children, className }: AuthSplitLayoutProps) {
  return (
    <div className={cn('grid min-h-screen lg:grid-cols-2', className)}>
      <div className="hidden bg-sidebar p-10 text-sidebar-foreground lg:flex lg:flex-col lg:justify-between">
        <MotionBrand />
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white">PRISM FinOps</h2>
          <p className="mt-3 max-w-md text-sm text-sidebar-foreground/80">
            Unified cloud cost intelligence across AWS, Azure, and Google Cloud — forecasts,
            commitments, and savings in one place.
          </p>
        </div>
        <p className="text-xs text-sidebar-foreground/60">© PRISM</p>
      </div>
      <div className="flex flex-col justify-center px-6 py-12 sm:px-12">
        <div className="mx-auto w-full max-w-md space-y-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            {subtitle ? <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p> : null}
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

function MotionBrand() {
  return <div className="text-xl font-bold text-white">PRISM</div>;
}
