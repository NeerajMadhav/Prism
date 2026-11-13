/** PRISM FinOps — login page. */

import type { Metadata } from 'next';

import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout';
import { LoginForm } from '@/components/auth/LoginForm';

export const metadata: Metadata = {
  title: 'Sign in',
};

export default function LoginPage() {
  return (
    <AuthSplitLayout title="Sign in" subtitle="Welcome back to PRISM">
      <LoginForm />
    </AuthSplitLayout>
  );
}
