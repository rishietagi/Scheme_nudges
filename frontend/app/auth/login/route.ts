import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { authConfig, same, SESSION_COOKIE, SESSION_DAYS, sessionToken, SIGNED_IN_COOKIE } from "@/lib/session";

// POST {username, password} → sets the session cookie when they match DEMO_USER / DEMO_PASSWORD.
export async function POST(request: NextRequest) {
  const auth = authConfig();
  if (!auth) return NextResponse.json({ ok: true }); // sign-in is off (local development)
  let body: { username?: string; password?: string } = {};
  try {
    body = await request.json();
  } catch {
    // treated as wrong credentials below
  }
  const user = (body.username ?? "").trim();
  const password = body.password ?? "";
  if (!same(user.toLowerCase(), auth.user.toLowerCase()) || !same(password, auth.password)) {
    await new Promise((r) => setTimeout(r, 400)); // slow down guessing a little
    return NextResponse.json({ ok: false, error: "That username or password isn't right." }, { status: 401 });
  }
  const secure = request.nextUrl.protocol === "https:" || request.headers.get("x-forwarded-proto") === "https";
  const options = { path: "/", sameSite: "lax" as const, secure, maxAge: SESSION_DAYS * 24 * 3600 };
  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, await sessionToken(auth.user, auth.password), { ...options, httpOnly: true });
  res.cookies.set(SIGNED_IN_COOKIE, "1", options);
  return res;
}
