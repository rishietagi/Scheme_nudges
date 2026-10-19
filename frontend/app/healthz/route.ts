// Health check for the host (kept outside the password gate in proxy.ts).
export function GET() {
  return new Response("ok", { headers: { "content-type": "text/plain" } });
}
