// Proxy to the backend /health so the client can poll without exposing
// API_URL or leaking CORS preflights. Returns 200 when backend is up,
// 503 otherwise. Never caches.

const API_URL = process.env.API_URL || "http://api:8000";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json", "cache-control": "no-store" } });
  } catch {
    // fall through
  }
  return new Response(JSON.stringify({ ok: false }), { status: 503, headers: { "content-type": "application/json", "cache-control": "no-store" } });
}
