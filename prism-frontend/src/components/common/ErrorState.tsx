/** PRISM FinOps — query error placeholder. */

import { AlertCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { extractErrorMessage } from '@/lib/utils/errors';

interface ErrorStateProps {
  title?: string;
  message?: string;
  error?: unknown;
  retry?: () => void;
  className?: string;
}

/** Shows a failed query with optional retry. */
export function ErrorState({
  title = 'Something went wrong',
  message,
  error,
  retry,
  className,
}: ErrorStateProps) {
  const detail = message ?? (error ? extractErrorMessage(error) : undefined);

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center px-4 py-16 text-center',
        className,
      )}
      role="alert"
    >
      <AlertCircle className="mb-3 size-10 text-destructive" aria-hidden />
      <h3 className="text-lg font-semibold">{title}</h3>
      {detail ? (
        <p className="mt-2 max-w-md text-sm text-muted-foreground">{detail}</p>
      ) : null}
      {retry ? (
        <Button variant="outline" className="mt-4" onClick={retry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}
