'use client';

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-2xl font-bold">Something went wrong</h1>
      {process.env.NODE_ENV === 'development' ? (
        <p className="max-w-lg text-sm text-muted-foreground">{error.message}</p>
      ) : (
        <p className="text-sm text-muted-foreground">Please try again or return to the dashboard.</p>
      )}
      <button
        type="button"
        className="rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white"
        onClick={reset}
      >
        Try again
      </button>
    </div>
  );
}
