/** PRISM FinOps — app header bar. */

'use client';

import { Search } from 'lucide-react';

import { CommandPalette } from '@/components/layout/CommandPalette';
import { NotificationsPanel } from '@/components/layout/NotificationsPanel';
import { UserMenu } from '@/components/layout/UserMenu';
import { Button } from '@/components/ui/button';
import { useOrg } from '@/lib/hooks/useOrg';
import { useUiStore } from '@/lib/store/uiStore';

export function TopBar() {
  const org = useOrg();
  const openCommandPalette = useUiStore((s) => s.openCommandPalette);

  return (
    <>
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card px-4 md:px-6">
        <div>
          <p className="text-xs text-muted-foreground">Organization</p>
          <p className="text-sm font-semibold">{org?.name ?? '—'}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="hidden gap-2 md:flex"
            onClick={openCommandPalette}
          >
            <Search className="size-4" />
            Search
            <span className="text-muted-foreground">⌘K</span>
          </Button>
          <NotificationsPanel />
          <UserMenu />
        </div>
      </header>
      <CommandPalette />
    </>
  );
}
