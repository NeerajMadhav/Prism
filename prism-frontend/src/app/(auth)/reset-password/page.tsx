'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout';
import { LoadingSkeleton } from '@/components/common/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ROUTES } from '@/lib/constants/routes';
import { useResetPassword } from '@/lib/hooks/useAuth';

const schema = z
  .object({
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm: z.string(),
  })
  .refine((data) => data.password === data.confirm, {
    message: 'Passwords do not match',
    path: ['confirm'],
  });

type FormValues = z.infer<typeof schema>;

function ResetPasswordForm() {
  const params = useSearchParams();
  const token = params.get('token') ?? '';
  const userId = params.get('user_id') ?? params.get('userId') ?? '';
  const reset = useResetPassword();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (!token || !userId) {
    return <p className="text-sm text-destructive">Reset link is incomplete.</p>;
  }

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((values) =>
        reset.mutate({ token, user_id: userId, new_password: values.password }),
      )}
      noValidate
    >
      <div className="space-y-2">
        <Label htmlFor="password">New password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          {...register('password')}
        />
        {errors.password ? (
          <p className="text-sm text-destructive">{errors.password.message}</p>
        ) : null}
      </div>
      <div className="space-y-2">
        <Label htmlFor="confirm">Confirm password</Label>
        <Input id="confirm" type="password" autoComplete="new-password" {...register('confirm')} />
        {errors.confirm ? (
          <p className="text-sm text-destructive">{errors.confirm.message}</p>
        ) : null}
      </div>
      <Button type="submit" className="w-full" disabled={reset.isPending}>
        {reset.isPending ? 'Saving…' : 'Set new password'}
      </Button>
      <p className="text-center text-sm">
        <Link href={ROUTES.login} className="text-primary hover:underline">
          Back to sign in
        </Link>
      </p>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthSplitLayout title="Reset password" subtitle="Choose a new password for your account">
      <Suspense fallback={<LoadingSkeleton />}>
        <ResetPasswordForm />
      </Suspense>
    </AuthSplitLayout>
  );
}
