/** PRISM FinOps — empty list placeholder. */

import type { LucideIcon } from 'lucide-react';
import { Inbox } from 'lucide-react';
import type { ReactNode } from 'react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface EmptyStateAction {
  label: string;
  onClick: () => void;
}

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  message?: ReactNode;
  action?: EmptyStateAction;
  className?: string;
}

/** Centered empty state with optional CTA. */
export function EmptyState({
  icon: Icon = Inbox,
  title,
  message,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center px-4 py-20 text-center',
        className,
      )}
    >
      <Icon className="mb-4 size-12 text-muted-foreground/50" aria-hidden />
      <h3 className="text-lg font-semibold">{title}</h3>
      {message ? (
        <p className="mt-2 max-w-md text-sm text-muted-foreground">{message}</p>
      ) : null}
      {action ? (
        <Button className="mt-6" onClick={action.onClick}>
          {action.label}
        </Button>
      ) : null}
    </div>
  );
}
