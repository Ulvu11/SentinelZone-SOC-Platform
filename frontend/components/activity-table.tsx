"use client";
import { useState } from "react";
import Link from "next/link";
import type { Severity } from "@/types";
import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import { SeverityBadge } from "@/components/severity-badge";
import { formatTime } from "@/lib/format";
import { inTimeRange, useTimeRange } from "@/components/time-range";
export interface ActivityRecord {
  id: string;
  title: string;
  timestamp: string;
  severity: Severity;
  href?: string;
  fields: Record<string, string>;
}
export function ActivityTable({
  records,
  columns,
}: {
  records: ActivityRecord[];
  columns: { key: string; header: string }[];
}) {
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const { range } = useTimeRange();
  const filtered = inTimeRange(records, range, (r) => r.timestamp).filter(
    (r) =>
      [r.id, r.title, ...Object.values(r.fields)]
        .join(" ")
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (!severity || r.severity === severity),
  );
  return (
    <>
      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search activity, IP, user or source"
        activeFilters={{ severity }}
        onFilterChange={(_, value) => setSeverity(value)}
        filters={[
          {
            key: "severity",
            label: "All severities",
            options: ["critical", "high", "medium", "low"].map((value) => ({
              label: value.toUpperCase(),
              value,
            })),
          },
        ]}
      />
      <p role="status" className="mb-3 text-xs text-soc-muted">
        {filtered.length} records in selected observation window
      </p>
      <DataTable
        data={filtered}
        keyExtractor={(r) => r.id}
        columns={[
          {
            key: "event",
            header: "Event",
            render: (r) => (
              <div className="min-w-48">
                <div className="mb-1 text-[10px] font-mono text-soc-muted">
                  {r.id}
                </div>
                {r.href ? (
                  <Link className="link" href={r.href}>
                    {r.title}
                  </Link>
                ) : (
                  r.title
                )}
              </div>
            ),
          },
          {
            key: "severity",
            header: "Severity",
            render: (r) => <SeverityBadge severity={r.severity} />,
          },
          ...columns.map((c) => ({
            ...c,
            render: (r: ActivityRecord) => (
              <span className="text-xs">{r.fields[c.key]}</span>
            ),
          })),
          {
            key: "time",
            header: "Observed",
            render: (r) => (
              <span className="whitespace-nowrap text-xs text-soc-muted">
                {formatTime(r.timestamp)}
              </span>
            ),
          },
        ]}
      />
    </>
  );
}
