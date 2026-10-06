"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Incident } from "@/types";
import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import { SeverityBadge } from "@/components/severity-badge";
import { IncidentStatusBadge } from "@/components/status-badge";
import { useTimeRange, inTimeRange } from "@/components/time-range";
import { formatTime } from "@/lib/format";
export function IncidentsTable({ incidents }: { incidents: Incident[] }) {
  const router = useRouter();
  const { range } = useTimeRange();
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const filtered = inTimeRange(incidents, range, (i) => i.createdAt).filter(
    (i) =>
      [
        i.id,
        i.title,
        i.affectedAsset,
        i.affectedUser,
        i.sourceIp,
        ...i.mitreTechniques,
      ]
        .join(" ")
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (!filters.severity || i.severity === filters.severity) &&
      (!filters.status || i.status === filters.status) &&
      (!filters.source || i.detectionSources.includes(filters.source)),
  );
  return (
    <>
      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search title, ID, asset, user, IP or technique"
        activeFilters={filters}
        onFilterChange={(key, value) =>
          setFilters((f) => ({ ...f, [key]: value }))
        }
        filters={[
          {
            key: "severity",
            label: "All severities",
            options: ["critical", "high", "medium", "low"].map((value) => ({
              label: value.toUpperCase(),
              value,
            })),
          },
          {
            key: "status",
            label: "All incident statuses",
            options: ["open", "investigating", "contained", "resolved"].map(
              (value) => ({ label: value, value }),
            ),
          },
          {
            key: "source",
            label: "All detection sources",
            options: [
              ...new Set(incidents.flatMap((i) => i.detectionSources)),
            ].map((value) => ({ label: value, value })),
          },
        ]}
      />
      <p role="status" className="mb-3 text-xs text-soc-muted">
        {filtered.length} matching incidents · selected time window ends at
        latest observation
      </p>
      <div className="overflow-hidden rounded-lg border border-soc-line bg-soc-panel">
        <DataTable
          data={filtered}
          keyExtractor={(i) => i.id}
          onRowClick={(i) => router.push("/incidents/" + i.id)}
          columns={[
            {
              key: "id",
              header: "Incident ID",
              render: (i) => (
                <Link
                  className="link whitespace-nowrap font-mono text-xs"
                  href={"/incidents/" + i.id}
                >
                  {i.id}
                </Link>
              ),
            },
            {
              key: "title",
              header: "Title",
              render: (i) => (
                <span className="block min-w-52 font-medium">{i.title}</span>
              ),
            },
            {
              key: "severity",
              header: "Severity",
              render: (i) => <SeverityBadge severity={i.severity} />,
            },
            {
              key: "status",
              header: "Status",
              render: (i) => <IncidentStatusBadge status={i.status} />,
            },
            { key: "asset", header: "Asset", render: (i) => i.affectedAsset },
            { key: "user", header: "User", render: (i) => i.affectedUser },
            {
              key: "ip",
              header: "Source IP",
              render: (i) => (
                <span className="font-mono text-xs">{i.sourceIp}</span>
              ),
            },
            {
              key: "sources",
              header: "Detection sources",
              render: (i) => (
                <div className="flex flex-wrap gap-1">
                  {i.detectionSources.map((s) => (
                    <span className="badge" key={s}>
                      {s}
                    </span>
                  ))}
                </div>
              ),
            },
            {
              key: "mitre",
              header: "MITRE techniques",
              render: (i) => (
                <div className="flex flex-wrap gap-1">
                  {i.mitreTechniques.map((t) => (
                    <Link key={t} className="badge link" href={"/mitre#" + t}>
                      {t}
                    </Link>
                  ))}
                </div>
              ),
            },
            {
              key: "confidence",
              header: "Confidence",
              render: (i) => i.confidence + "%",
            },
            {
              key: "created",
              header: "Created",
              render: (i) => (
                <span className="whitespace-nowrap text-xs text-soc-muted">
                  {formatTime(i.createdAt)}
                </span>
              ),
            },
            {
              key: "analyst",
              header: "Assigned analyst",
              render: (i) => i.assignedTo ?? "Unassigned",
            },
          ]}
        />
      </div>
    </>
  );
}
