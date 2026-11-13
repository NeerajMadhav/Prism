/** PRISM FinOps — Google OAuth entry button. */

'use client';

import { startGoogleOAuth } from '@/lib/api/auth';
import { Button } from '@/components/ui/button';

export function GoogleOAuthButton() {
  const href = startGoogleOAuth();

  return (
    <Button
      type="button"
      variant="outline"
      className="w-full"
      onClick={() => {
        window.location.href = href;
      }}
    >
      Continue with Google
    </Button>
  );
}
