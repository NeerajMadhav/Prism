/** PRISM FinOps — primary app navigation sidebar. */

'use client';

import {
  AlertTriangle,
  BarChart3,
  Bot,
  Boxes,
  Cloud,
  FileText,
  Gauge,
  Layers,
  LineChart,
  PanelLeftClose,
  PanelLeftOpen,
  PiggyBank,
  Receipt,
  Shield,
  Sparkles,
  Tag,
  Target,
  Wand2,
} from 'lucide-react';
import Link from 'next/link';

import { SidebarItem } from '@/components/layout/SidebarItem';
import { Button } from '@/components/ui/button';
import { ROUTES } from '@/lib/constants/routes';
import { useUiStore } from '@/lib/store/uiStore';
import { cn } from '@/lib/utils';

const NAV = [
  { href: ROUTES.dashboard, label: 'Dashboard', icon: Gauge },
  { href: ROUTES.costs, label: 'Costs', icon: Receipt },
  { href: ROUTES.accounts, label: 'Accounts', icon: Cloud },
  { href: ROUTES.forecasts, label: 'Forecasts', icon: LineChart },
  { href: ROUTES.commitments, label: 'Commitments', icon: PiggyBank },
  { href: ROUTES.recommendations, label: 'Recommendations', icon: Sparkles },
  { href: ROUTES.scorecard, label: 'Scorecard', icon: Target },
  { href: ROUTES.resources, label: 'Resources', icon: Boxes },
  { href: ROUTES.caps, label: 'Budget Caps', icon: Shield },
  { href: ROUTES.alerts, label: 'Alerts', icon: AlertTriangle },
  { href: ROUTES.virtualTags, label: 'Virtual Tags', icon: Tag },
  { href: ROUTES.metrics, label: 'Metrics', icon: BarChart3 },
  { href: ROUTES.assistant, label: 'Assistant', icon: Bot },
  { href: ROUTES.reports, label: 'Reports', icon: FileText },
  { href: ROUTES.onboarding, label: 'Onboarding', icon: Wand2 },
] as const;

export function Sidebar() {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);

  return (
    <aside
      className={cn(
        'hidden h-full shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:flex',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      <div className="flex h-14 items-center justify-between border-b border-sidebar-border px-3">
        <Link href={ROUTES.dashboard} className="font-semibold tracking-tight text-white">
          {collapsed ? 'P' : 'PRISM'}
        </Link>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-white"
          onClick={toggleSidebar}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeftOpen className="size-4" /> : <PanelLeftClose className="size-4" />}
        </Button>
      </div>
      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
        {NAV.map((item) => (
          <SidebarItem key={item.href} {...item} collapsed={collapsed} />
        ))}
      </nav>
      <div className="border-t border-sidebar-border p-2">
        <SidebarItem
          href={ROUTES.settingsProfile}
          label="Settings"
          icon={Layers}
          collapsed={collapsed}
        />
      </div>
    </aside>
  );
}
