'use client';

import { useSearchParams } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useVerifyEmail } from '@/lib/hooks/useAuth';

export function VerifyEmailForm() {
  const params = useSearchParams();
  const userId = params.get('user_id') ?? '';
  const verify = useVerifyEmail();
  const [token, setToken] = useState('');

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        verify.mutate({ token, user_id: userId });
      }}
    >
      <div className="space-y-2">
        <Label htmlFor="token">Verification token</Label>
        <Input id="token" value={token} onChange={(e) => setToken(e.target.value)} />
      </div>
      <Button type="submit" className="w-full" disabled={!token || verify.isPending}>
        Verify email
      </Button>
    </form>
  );
}
