import type { Metadata } from 'next';

import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout';
import { SignupForm } from '@/components/auth/SignupForm';

export const metadata: Metadata = {
  title: 'Sign up',
};

export default function SignupPage() {
  return (
    <AuthSplitLayout title="Sign up" subtitle="Create your PRISM workspace">
      <SignupForm />
    </AuthSplitLayout>
  );
}
