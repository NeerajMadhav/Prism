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
import { useMe } from '@/lib/hooks/useAuth';
import { useAcceptInvite } from '@/lib/hooks/useTeam';

const schema = z.object({
  name: z.string().min(2, 'Name is required').optional(),
  password: z.string().min(8, 'Password must be at least 8 characters').optional(),
});

type FormValues = z.infer<typeof schema>;

function AcceptInviteForm() {
  const params = useSearchParams();
  const token = params.get('token') ?? '';
  const orgId = params.get('org_id') ?? params.get('orgId') ?? '';
  const me = useMe(Boolean(token));
  const accept = useAcceptInvite(orgId);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (!token || !orgId) {
    return <p className="text-sm text-destructive">Invite link is incomplete.</p>;
  }

  const existingUser = Boolean(me.data);

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((values) =>
        accept.mutate({
          token,
          name: values.name,
          password: values.password,
        }),
      )}
      noValidate
    >
      <p className="text-sm text-muted-foreground">
        {existingUser
          ? 'Join the organization with your current account.'
          : 'Create your profile to join the organization.'}
      </p>
      {!existingUser ? (
        <>
          <div className="space-y-2">
            <Label htmlFor="name">Your name</Label>
            <Input id="name" autoComplete="name" {...register('name')} />
            {errors.name ? (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
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
        </>
      ) : null}
      <Button type="submit" className="w-full" disabled={accept.isPending}>
        {accept.isPending ? 'Joining…' : 'Accept invite'}
      </Button>
      {accept.isError ? <p className="text-sm text-destructive">Invite expired or invalid.</p> : null}
      <p className="text-center text-sm">
        <Link href={ROUTES.login} className="text-primary hover:underline">
          Sign in instead
        </Link>
      </p>
    </form>
  );
}

export default function AcceptInvitePage() {
  return (
    <AuthSplitLayout title="Accept invitation" subtitle="Join your team workspace">
      <Suspense fallback={<LoadingSkeleton />}>
        <AcceptInviteForm />
      </Suspense>
    </AuthSplitLayout>
  );
}
