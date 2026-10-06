import "server-only";
export class BackendError extends Error {
  constructor(public code: string, public status = 503) { super(code); }
}
export async function backend<T>(path: string): Promise<T> {
  const url = process.env.SENTINELZONE_API_URL;
  const token = process.env.SENTINELZONE_API_TOKEN;
  if (!url || !token) throw new BackendError("not_configured");
  let base: URL;
  try {
    base = new URL(url);
    if (base.username || base.password || base.search || base.hash || base.pathname !== "/" ||
      (base.protocol !== "https:" && !(base.protocol === "http:" && ["127.0.0.1", "localhost", "[::1]"].includes(base.hostname)))) throw new Error();
    if (!path.startsWith("/v1/") && path !== "/health") throw new Error();
  } catch { throw new BackendError("invalid_configuration"); }
  try {
    const response = await fetch(new URL(path, base), { cache: "no-store", redirect: "error", headers: { Authorization: `Bearer ${token}`, Accept: "application/json" }, signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new BackendError(response.status === 404 ? "not_found" : response.status === 401 || response.status === 403 ? "backend_auth_unavailable" : "backend_unavailable", response.status === 404 ? 404 : 503);
    if (!response.headers.get("content-type")?.includes("application/json") || !response.body) throw new BackendError("invalid_response");
    const reader = response.body.getReader(); const chunks: Uint8Array[] = []; let length = 0;
    while (true) { const { value, done } = await reader.read(); if (done) break; length += value.byteLength; if (length > 32 * 1024 * 1024) { await reader.cancel(); throw new BackendError("response_too_large"); } chunks.push(value); }
    return JSON.parse(Buffer.concat(chunks).toString("utf8")) as T;
  } catch (e) { if (e instanceof BackendError) throw e; throw new BackendError("backend_unavailable"); }
}
