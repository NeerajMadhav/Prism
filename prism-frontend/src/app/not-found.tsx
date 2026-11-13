import Link from 'next/link';

import { ROUTES } from '@/lib/constants/routes';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-bold">Page not found</h1>
      <Link href={ROUTES.dashboard} className="text-brand-600 hover:underline">
        Back to dashboard
      </Link>
    </div>
  );
}
