/** PRISM FinOps — semantic status indicator dot. */

import { cn } from '@/lib/utils';

type StatusTone = 'success' | 'warning' | 'danger' | 'muted' | 'info';

interface StatusDotProps {
  tone?: StatusTone;
  pulse?: boolean;
  label?: string;
  className?: string;
}

const TONE_CLASS: Record<StatusTone, string> = {
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-destructive',
  muted: 'bg-muted-foreground',
  info: 'bg-primary',
};

export function StatusDot({ tone = 'muted', pulse, label, className }: StatusDotProps) {
  return (
    <span
      className={cn('inline-flex items-center gap-2 text-sm', className)}
      title={label}
    >
      <span className="relative flex size-2">
        {pulse ? (
          <span
            className={cn(
              'absolute inline-flex size-full animate-ping rounded-full opacity-60',
              TONE_CLASS[tone],
            )}
          />
        ) : null}
        <span
          className={cn('relative inline-flex size-2 rounded-full', TONE_CLASS[tone])}
          aria-hidden
        />
      </span>
      {label ? <span className="text-muted-foreground">{label}</span> : null}
    </span>
  );
}
