import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Password gate for the hosted review copy: when DEMO_PASSWORD is set (on the server only), every page and API call
// asks for a shared username/password (browser login prompt). Locally it's unset, so nothing changes.
export function proxy(request: NextRequest) {
  const password = process.env.DEMO_PASSWORD;
  if (!password) return NextResponse.next();
  const user = process.env.DEMO_USER || "emami";
  const header = request.headers.get("authorization") ?? "";
  if (header.startsWith("Basic ")) {
    try {
      const [u, ...rest] = atob(header.slice(6)).split(":");
      if (u === user && rest.join(":") === password) return NextResponse.next();
    } catch {
      // fall through to the prompt
    }
  }
  return new NextResponse("Sign in to view the Emami Distributor Experience Platform (concept prototype).", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Emami DX prototype", charset="UTF-8"' },
  });
}

export const config = {
  // Everything except the health check and Next's own static files and icons.
  matcher: ["/((?!healthz|brand/|_next/static|_next/image|favicon.ico).*)"],
};
