/** PRISM FinOps — settings section layout. */

import type { ReactNode } from 'react';

import { SettingsSubNav } from '@/components/layout/SettingsSubNav';

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <div>
      <SettingsSubNav />
      {children}
    </div>
  );
}
