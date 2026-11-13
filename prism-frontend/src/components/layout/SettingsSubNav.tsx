/** PRISM FinOps — settings section sub-navigation. */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { ROUTES } from '@/lib/constants/routes';
import { cn } from '@/lib/utils';

const LINKS = [
  { href: ROUTES.settingsProfile, label: 'Profile' },
  { href: ROUTES.settingsOrg, label: 'Organization' },
  { href: ROUTES.settingsTeam, label: 'Team' },
  { href: ROUTES.settingsNotifications, label: 'Notifications' },
  { href: ROUTES.settingsWebhooks, label: 'Webhooks' },
  { href: ROUTES.settingsApiKeys, label: 'API Keys' },
  { href: ROUTES.settingsLlm, label: 'LLM' },
] as const;

export function SettingsSubNav() {
  const pathname = usePathname();

  return (
    <nav className="mb-6 flex flex-wrap gap-2 border-b border-border pb-4">
      {LINKS.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
              active
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground',
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
