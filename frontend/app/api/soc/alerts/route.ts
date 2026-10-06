import { readSocAlerts, AlertSourceError } from "@/lib/soc-alerts-source";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request:Request) {
  const headers = { "Cache-Control": "no-store, max-age=0" };
  try { return Response.json(await readSocAlerts(new URL(request.url).searchParams.get('range')??'24h'), { headers }); }
  catch (error) {
    const code = error instanceof AlertSourceError ? error.code : "unavailable";
    return Response.json({ status: code, alerts: null }, { status: 503, headers });
  }
}
