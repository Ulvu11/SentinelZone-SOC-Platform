"use client";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { ThreatHuntQuery, ThreatHuntResult } from "@/types";
import { Panel } from "@/components/panel";
import { DataTable } from "@/components/data-table";
import { SeverityBadge } from "@/components/severity-badge";
import { LoadingState } from "@/components/loading-state";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { useTimeRange } from "@/components/time-range";
import { formatTime } from "@/lib/format";
export function ThreatHuntWorkspace() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [results, setResults] = useState<ThreatHuntResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { range } = useTimeRange();
  const hunt = async () => {
    setLoading(true);
    setError("");
    try {
      setResults(
        await api.threatHunt({
          query,
          entityType: (type || undefined) as ThreatHuntQuery["entityType"],
          timeRange: range,
        }),
      );
    } catch {
      setError("Threat search could not complete. Try again.");
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="space-y-4">
      <Panel
        title="Indicator Search"
        subtitle="Search across correlated endpoint, identity and detection evidence"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void hunt();
          }}
          className="flex flex-wrap gap-3"
        >
          <input
            className="control min-w-48 flex-1"
            aria-label="Hunt query"
            placeholder="IP, hostname, username, process, SHA-256 or incident ID"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            className="control"
            aria-label="Entity type"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            <option value="">All entity types</option>
            {["ip", "hostname", "username", "process", "hash", "incident"].map(
              (t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ),
            )}
          </select>
          <button className="button" disabled={loading}>
            Run hunt
          </button>
        </form>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-soc-muted">
          <span>Examples:</span>
          {["185.220.101.42", "FINANCE-PC-021", "svhost64.exe", "INC-0042"].map(
            (q) => (
              <button
                className="badge hover:border-soc-accent"
                key={q}
                onClick={() => setQuery(q)}
              >
                {q}
              </button>
            ),
          )}
        </div>
      </Panel>
      <Panel
        title="Hunt Results"
        subtitle="The selected global time range is applied when you run a hunt"
      >
        {loading ? (
          <LoadingState message="Correlating indicators…" />
        ) : error ? (
          <ErrorState message={error} onRetry={() => void hunt()} />
        ) : results === null ? (
          <EmptyState
            title="Ready to investigate"
            description="Enter an indicator or leave the query empty to inspect the selected scope."
          />
        ) : (
          <>
            <p role="status" className="mb-3 text-xs text-soc-muted">
              {results.length} matching records
            </p>
            <DataTable
              data={results}
              keyExtractor={(r) => r.id}
              columns={[
                {
                  key: "value",
                  header: "Indicator",
                  render: (r) => (
                    <div className="max-w-80 break-all">
                      <span className="badge mb-1">{r.entityType}</span>
                      <p>
                        {r.href ? (
                          <Link
                            className="link font-mono text-xs"
                            href={r.href}
                          >
                            {r.value}
                          </Link>
                        ) : (
                          r.value
                        )}
                      </p>
                    </div>
                  ),
                },
                {
                  key: "severity",
                  header: "Severity",
                  render: (r) => <SeverityBadge severity={r.severity} />,
                },
                { key: "source", header: "Source", render: (r) => r.source },
                { key: "summary", header: "Context", render: (r) => r.summary },
                {
                  key: "incident",
                  header: "Related incidents",
                  render: (r) =>
                    r.relatedIncidentIds.map((id) => (
                      <Link
                        key={id}
                        className="link block text-xs"
                        href={"/incidents/" + id}
                      >
                        {id}
                      </Link>
                    )),
                },
                {
                  key: "time",
                  header: "Observed",
                  render: (r) => formatTime(r.timestamp),
                },
              ]}
            />
          </>
        )}
      </Panel>
    </div>
  );
}
