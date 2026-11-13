/** PRISM FinOps — copy-to-clipboard monospace block. */

'use client';

import { Check, Copy } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface CopyBlockProps {
  value: string;
  label?: string;
  className?: string;
}

export function CopyBlock({ value, label, className }: CopyBlockProps) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      toast.success('Copied');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Could not copy');
    }
  }

  return (
    <div className={cn('rounded-lg border bg-muted/40 p-3', className)}>
      {label ? <p className="mb-1 text-xs font-medium text-muted-foreground">{label}</p> : null}
      <div className="flex items-start gap-2">
        <code className="flex-1 break-all font-mono text-xs">{value}</code>
        <Button type="button" size="icon" variant="ghost" onClick={copy} aria-label="Copy">
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
        </Button>
      </div>
    </div>
  );
}
