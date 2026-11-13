/** PRISM FinOps — ⌘K command palette. */

'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { ROUTES } from '@/lib/constants/routes';
import { useUiStore } from '@/lib/store/uiStore';

const PAGES = [
  { label: 'Dashboard', href: ROUTES.dashboard },
  { label: 'Costs', href: ROUTES.costs },
  { label: 'Accounts', href: ROUTES.accounts },
  { label: 'Alerts', href: ROUTES.alerts },
  { label: 'Budget Caps', href: ROUTES.caps },
  { label: 'Forecasts', href: ROUTES.forecasts },
  { label: 'Recommendations', href: ROUTES.recommendations },
  { label: 'Scorecard', href: ROUTES.scorecard },
  { label: 'Resources', href: ROUTES.resources },
  { label: 'Settings', href: ROUTES.settingsProfile },
];

export function CommandPalette() {
  const router = useRouter();
  const open = useUiStore((s) => s.commandPaletteOpen);
  const openPalette = useUiStore((s) => s.openCommandPalette);
  const closePalette = useUiStore((s) => s.closeCommandPalette);
  const recentPages = useUiStore((s) => s.recentPages);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (open) closePalette();
        else openPalette();
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [closePalette, open, openPalette]);

  function go(href: string) {
    closePalette();
    router.push(href);
  }

  return (
    <CommandDialog open={open} onOpenChange={(next) => (next ? openPalette() : closePalette())}>
      <CommandInput placeholder="Search pages and actions…" />
      <CommandList>
        <CommandEmpty>No results found</CommandEmpty>
        <CommandGroup heading="Pages">
          {PAGES.map((page) => (
            <CommandItem key={page.href} onSelect={() => go(page.href)}>
              {page.label}
            </CommandItem>
          ))}
        </CommandGroup>
        {recentPages.length > 0 ? (
          <CommandGroup heading="Recent">
            {recentPages.map((path) => (
              <CommandItem key={path} onSelect={() => go(path)}>
                {path}
              </CommandItem>
            ))}
          </CommandGroup>
        ) : null}
        <CommandGroup heading="Actions">
          <CommandItem onSelect={() => go(ROUTES.accountsConnect)}>Connect account</CommandItem>
          <CommandItem onSelect={() => go(ROUTES.caps)}>Create cap</CommandItem>
          <CommandItem onSelect={() => go(ROUTES.alerts)}>View alerts</CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
