/** PRISM FinOps — Microsoft Entra OAuth entry button. */

'use client';

import { startMicrosoftOAuth } from '@/lib/api/auth';
import { Button } from '@/components/ui/button';

export function MicrosoftOAuthButton() {
  const href = startMicrosoftOAuth();

  return (
    <Button
      type="button"
      variant="outline"
      className="w-full"
      onClick={() => {
        window.location.href = href;
      }}
    >
      Continue with Microsoft
    </Button>
  );
}
