/** PRISM FinOps — password strength meter. */

'use client';

import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface PasswordStrengthBarProps {
  password: string;
  className?: string;
}

function scorePassword(password: string): { score: number; label: string } {
  let score = 0;
  if (password.length >= 8) {
    score += 1;
  }
  if (password.length >= 12) {
    score += 1;
  }
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) {
    score += 1;
  }
  if (/\d/.test(password)) {
    score += 1;
  }
  if (/[^a-zA-Z0-9]/.test(password)) {
    score += 1;
  }
  const labels = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very strong'];
  const idx = Math.min(score, labels.length - 1);
  return { score: (score / 5) * 100, label: password ? labels[idx] : '' };
}

/** Visual password strength indicator for auth forms. */
export function PasswordStrengthBar({ password, className }: PasswordStrengthBarProps) {
  const { score, label } = scorePassword(password);

  if (!password) {
    return null;
  }

  return (
    <div className={cn('space-y-1', className)}>
      <Progress value={score} className="h-1.5" />
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}
