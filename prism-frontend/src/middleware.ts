/** PRISM FinOps — edge routing helper (auth is Bearer + AuthBootstrap, not cookies). */

import { NextResponse, type NextRequest } from 'next/server';

import { PUBLIC_ROUTES, ROUTES } from '@/lib/constants/routes';
import { safeRedirectPath } from '@/lib/utils/safeRedirect';

/**
 * Soft UX gate only: unsigned cookies are not trusted as authentication.
 * Real authorization is enforced by the API (JWT/API key + org membership).
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_ROUTES.has(pathname);

  // Do not redirect away from login/signup based on a forgeable cookie.
  if (!isPublic && pathname !== '/' && pathname !== ROUTES.login && pathname !== ROUTES.signup) {
    // Pass through — client AuthBootstrap decides authenticated vs login.
    return NextResponse.next();
  }

  // Normalize `from` on login links generated elsewhere (defense in depth).
  if (pathname === ROUTES.login) {
    const from = request.nextUrl.searchParams.get('from');
    if (from) {
      const safe = safeRedirectPath(from, ROUTES.dashboard);
      if (safe !== from) {
        const url = request.nextUrl.clone();
        url.searchParams.set('from', safe);
        return NextResponse.redirect(url);
      }
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|providers|.*\\..*).*)'],
};
