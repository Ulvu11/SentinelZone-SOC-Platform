import { backend, BackendError } from "@/lib/sentinelzone-backend";
import type { SocReport } from "@/lib/soc-report";

export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const from = params.get("from"), to = params.get("to");
  const aware = /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/;
  if (!from || !to || !aware.test(from) || !aware.test(to) || !Number.isFinite(Date.parse(from)) || !Number.isFinite(Date.parse(to)) || Date.parse(from) >= Date.parse(to) || Date.parse(to) - Date.parse(from) > 31 * 86400000) {
    return Response.json({ error: "Select a valid time range of up to 31 days." }, { status: 400, headers: { "Cache-Control": "no-store" } });
  }
  try {
    const report = await backend<SocReport>(`/v1/reports/soc-summary?${new URLSearchParams({ from, to })}`);
    return Response.json(report, { headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
  } catch (error) {
    const code = error instanceof BackendError ? error.code : "backend_unavailable";
    return Response.json({ error: code === "not_configured" ? "Not configured" : "Unavailable — SentinelZone could not provide the report." }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}
