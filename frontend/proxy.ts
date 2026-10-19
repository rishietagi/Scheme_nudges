import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { authConfig, same, SESSION_COOKIE, sessionToken } from "@/lib/session";

// Sign-in gate for the hosted review copy (see lib/session.ts). Pages without a valid session go to /login; API calls
// get a 401. With no DEMO_PASSWORD (local development) everything is open.
export async function proxy(request: NextRequest) {
  const auth = authConfig();
  if (!auth) return NextResponse.next();
  const cookie = request.cookies.get(SESSION_COOKIE)?.value ?? "";
  if (cookie && same(cookie, await sessionToken(auth.user, auth.password))) return NextResponse.next();

  const { pathname, search } = request.nextUrl;
  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ detail: "Sign in first" }, { status: 401 });
  }
  const login = new URL("/login", request.url);
  if (pathname !== "/") login.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(login);
}

export const config = {
  // Everything except the sign-in page and its handlers, the health check, the logo files and Next's own assets.
  matcher: ["/((?!login|auth/|healthz|brand/|_next/static|_next/image|favicon.ico).*)"],
};
