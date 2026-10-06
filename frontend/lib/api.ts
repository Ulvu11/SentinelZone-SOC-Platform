import { createApi } from "./api-factory";
export const api = createApi(async <T>(path: string, body?: unknown): Promise<T> => {
  const response = await fetch(`/api/sentinelzone/${path}`, { method: body === undefined ? "GET" : "POST", cache: "no-store", headers: body === undefined ? undefined : { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
  if (!response.ok) throw new Error("SentinelZone data unavailable");
  return response.json();
});
