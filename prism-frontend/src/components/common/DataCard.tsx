/** PRISM FinOps — KPI / metric card shell. */

import type { ReactNode } from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface DataCardProps {
  title: string;
  value: ReactNode;
  subtitle?: ReactNode;
  footer?: ReactNode;
  className?: string;
}

export function DataCard({ title, value, subtitle, footer, className }: DataCardProps) {
  return (
    <Card className={cn('shadow-sm', className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <div className="text-2xl font-bold tracking-tight">{value}</div>
        {subtitle ? <div className="text-sm text-muted-foreground">{subtitle}</div> : null}
        {footer ? <div className="pt-2">{footer}</div> : null}
      </CardContent>
    </Card>
  );
}
