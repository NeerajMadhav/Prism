/** PRISM FinOps — organization signup form. */

'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { GoogleOAuthButton } from '@/components/auth/GoogleOAuthButton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { ROUTES } from '@/lib/constants/routes';
import { useSignup } from '@/lib/hooks/useAuth';
import { passwordSchema } from '@/lib/validation/password';

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Enter a valid email'),
  password: passwordSchema,
  org_name: z.string().min(1, 'Organization name is required'),
});

type FormValues = z.infer<typeof schema>;

export function SignupForm() {
  const signup = useSignup();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((values) => signup.mutate(values))}
      noValidate
    >
      <div className="space-y-2">
        <Label htmlFor="name">Your name</Label>
        <Input id="name" autoComplete="name" {...register('name')} />
        {errors.name ? <p className="text-sm text-destructive">{errors.name.message}</p> : null}
      </div>
      <div className="space-y-2">
        <Label htmlFor="org_name">Organization</Label>
        <Input id="org_name" {...register('org_name')} />
        {errors.org_name ? (
          <p className="text-sm text-destructive">{errors.org_name.message}</p>
        ) : null}
      </div>
      <div className="space-y-2">
        <Label htmlFor="email">Work email</Label>
        <Input id="email" type="email" autoComplete="email" {...register('email')} />
        {errors.email ? (
          <p className="text-sm text-destructive">{errors.email.message}</p>
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
      <Button type="submit" className="w-full" disabled={signup.isPending}>
        {signup.isPending ? 'Creating account…' : 'Create account'}
      </Button>
      <Separator />
      <GoogleOAuthButton />
      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{' '}
        <Link href={ROUTES.login} className="text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
