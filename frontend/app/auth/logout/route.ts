import { NextResponse } from "next/server";
import { SESSION_COOKIE, SIGNED_IN_COOKIE } from "@/lib/session";

// POST → clears the session; the page then goes to /login.
export function POST() {
  const res = NextResponse.json({ ok: true });
  res.cookies.delete(SESSION_COOKIE);
  res.cookies.delete(SIGNED_IN_COOKIE);
  return res;
}
