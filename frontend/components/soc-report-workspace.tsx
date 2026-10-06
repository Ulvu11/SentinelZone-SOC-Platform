"use client";
import { useEffect, useState } from "react";
import { Download, Printer, RefreshCw } from "lucide-react";
import { Panel } from "@/components/panel";
import { useTimeRange } from "@/components/time-range";
import { reportCsv, reportSections, reportValue, type SocReport } from "@/lib/soc-report";

const localInput = (date: Date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
export function SocReportWorkspace() {
  const { range } = useTimeRange();
  const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const [request, setRequest] = useState<{ from: string; to: string; id: number } | null>(null);
  const [report, setReport] = useState<SocReport | null>(null);
  const [error, setError] = useState(""); const [loading, setLoading] = useState(true); const [status, setStatus] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const end = request ? new Date(request.to) : new Date();
    const start = request ? new Date(request.from) : new Date(end.getTime() - (range === "1h" ? 1 : range === "7d" ? 168 : 24) * 3600000);
    async function load() {
      setLoading(true); setError(""); setReport(null); setStatus(""); setFrom(localInput(start)); setTo(localInput(end));
      try {
        const response = await fetch(`/api/reports/soc-summary?${new URLSearchParams({ from: start.toISOString(), to: end.toISOString() })}`, { cache: "no-store", signal: controller.signal });
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Unavailable");
        if (!controller.signal.aborted) setReport(body);
      } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "Unavailable"); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load(); return () => controller.abort();
  }, [range, request]);
  const exportReport = (format: "json" | "csv") => {
    if (!report) return;
    const url = URL.createObjectURL(new Blob([format === "json" ? JSON.stringify(report, null, 2) : reportCsv(report)], { type: format === "json" ? "application/json;charset=utf-8" : "text/csv;charset=utf-8" }));
    const a = document.createElement("a"); a.href = url; a.download = `sentinelzone-soc-summary-${report.generated_at.replaceAll(":", "-")}.${format}`;
    a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); setStatus(`${format.toUpperCase()} exported from the displayed report.`);
  };
  return <div className="space-y-5">
    <form className="report-controls flex flex-wrap items-end gap-3 rounded-lg border border-soc-line bg-soc-panel p-4" onSubmit={e => {
      e.preventDefault(); const start = Date.parse(from), end = Date.parse(to);
      if (!Number.isFinite(start) || !Number.isFinite(end) || start >= end || end - start > 31 * 86400000) { setError("Select a valid range of up to 31 days."); setReport(null); return; }
      setRequest({ from: new Date(start).toISOString(), to: new Date(end).toISOString(), id: Date.now() });
    }}>
      <label className="grid gap-1 text-xs text-soc-muted">From (local time)<input className="control" type="datetime-local" required value={from} onChange={e => setFrom(e.target.value)} /></label>
      <label className="grid gap-1 text-xs text-soc-muted">To (local time)<input className="control" type="datetime-local" required value={to} onChange={e => setTo(e.target.value)} /></label>
      <button className="button" type="submit" disabled={loading}><RefreshCw size={14} />{loading ? "Generating…" : "Generate report"}</button>
      <button className="button" type="button" onClick={() => setRequest(null)} disabled={loading || !request}>Use header time range</button>
      <span className="text-xs text-soc-muted">Maximum 31 days. The report retains its own generated range.</span>
    </form>
    <div role="status" aria-live="polite" className="report-controls text-sm text-soc-muted">{loading ? "Reading real SentinelZone data…" : error || status}</div>
    {report && <article className="soc-report space-y-5">
      <Panel title={report.title} subtitle={`Tenant: ${report.tenant} · Generated: ${report.generated_at}`} action={<div className="report-controls flex flex-wrap gap-2">
        <button className="button" onClick={() => exportReport("json")}><Download size={14} />Export JSON</button>
        <button className="button" onClick={() => exportReport("csv")}><Download size={14} />Export CSV</button>
        <button className="button" onClick={() => window.print()}><Printer size={14} />Print / Save as PDF</button>
      </div>}>
        <p className="mb-3 text-sm">{report.time_range.from} → {report.time_range.to}</p>
        <div className="grid gap-3 sm:grid-cols-3">{([["Alerts", report.alerts.count], ["Incidents", report.incidents.count], ["Open incidents", report.incidents.open_count]] as const).map(([label, value]) => <div className="rounded-lg border border-soc-line p-3" key={label}><div className="text-xs text-soc-muted">{label}</div><strong className="text-xl">{reportValue(value)}</strong></div>)}</div>
        {!report.data_complete && <p className="mt-3 text-sm text-soc-muted">Coverage is incomplete. Counts describe stored observations; they do not establish that every source is healthy. Inspect connector availability below.</p>}
      </Panel>
      {reportSections(report).map(section => <Panel key={section.title} title={section.title} subtitle={section.description}>
        {section.rows.length ? <div className="report-table overflow-x-auto"><table className="w-full text-xs"><thead><tr>{section.headers.map(header => <th key={header} scope="col" className="border-b border-soc-line p-2 text-left text-soc-muted">{header}</th>)}</tr></thead><tbody>{section.rows.map((row, index) => <tr key={index}>{row.map((cell, column) => <td key={column} className="border-b border-soc-line p-2 align-top break-words">{cell}</td>)}</tr>)}</tbody></table></div> : <p className="text-sm text-soc-muted">Unavailable — no matching records in the selected range.</p>}
      </Panel>)}
    </article>}
  </div>;
}
