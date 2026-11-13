/** PRISM FinOps — cloud provider pill. */

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { getProviderColor, getProviderLabel, isValidProvider } from '@/lib/utils/providers';

interface ProviderBadgeProps {
  provider: string;
  className?: string;
}

export function ProviderBadge({ provider, className }: ProviderBadgeProps) {
  const color = getProviderColor(provider);
  const label = getProviderLabel(provider);

  return (
    <Badge
      variant="outline"
      className={cn('border-transparent font-medium', className)}
      style={{
        backgroundColor: isValidProvider(provider) ? `${color}20` : undefined,
        color,
      }}
    >
      {label}
    </Badge>
  );
}
