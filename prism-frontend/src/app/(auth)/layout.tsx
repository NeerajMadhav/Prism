/** PRISM FinOps — unauthenticated route group layout. */

import type { ReactNode } from 'react';

export default function AuthGroupLayout({ children }: { children: ReactNode }) {
  return <div className="min-h-screen bg-background">{children}</div>;
}
