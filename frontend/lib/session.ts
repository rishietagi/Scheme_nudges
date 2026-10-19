// Sign-in for the hosted review copy. When DEMO_PASSWORD is set (server only), every page and API call needs a session
// cookie, which the in-app /login page sets after checking the shared username and password. Locally it's unset, so the
// app is open. The cookie is an HMAC of the credentials: no session store, and changing the password signs everyone out.

export const SESSION_COOKIE = "emami_dx_session";
export const SIGNED_IN_COOKIE = "emami_dx_signed_in"; // readable by the page, only to show "Sign out"
export const SESSION_DAYS = 7;

export function authConfig(): { user: string; password: string } | null {
  const password = process.env.DEMO_PASSWORD;
  if (!password) return null;
  return { user: process.env.DEMO_USER || "emami", password };
}

export async function sessionToken(user: string, password: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey("raw", enc.encode(password), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(`emami-dx-session:${user}`));
  return Array.from(new Uint8Array(sig), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Constant-time-ish string compare (same length check first). */
export function same(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
