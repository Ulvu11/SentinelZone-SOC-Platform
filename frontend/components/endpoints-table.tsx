"use client";
import { displayMetric } from "@/lib/format";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Endpoint } from "@/types";
import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import { SecurityRiskBadge, HardwareRiskBadge } from "@/components/risk-badge";
import { EndpointStatusBadge } from "@/components/status-badge";
import { formatTime, riskLevel } from "@/lib/format";
export function EndpointsTable({ endpoints }: { endpoints: Endpoint[] }) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [sort, setSort] = useState("security-desc");
  const filtered = endpoints
    .filter(
      (e) =>
        [e.hostname, e.ip, e.user, e.os].some((v) =>
          v.toLowerCase().includes(search.toLowerCase()),
        ) &&
        (!filters.status || e.status === filters.status) &&
        (!filters.security || riskLevel(e.securityRisk) === filters.security) &&
        (!filters.hardware || riskLevel(e.hardwareRisk) === filters.hardware),
    )
    .sort((a, b) =>
      sort === "hostname"
        ? a.hostname.localeCompare(b.hostname)
        : sort === "hardware-desc"
          ? (b.hardwareRisk ?? -1) - (a.hardwareRisk ?? -1)
          : sort === "cpu-desc"
            ? (b.cpu ?? -1) - (a.cpu ?? -1)
            : sort === "seen-desc"
              ? b.lastSeen.localeCompare(a.lastSeen)
              : sort === "security-asc"
                ? (a.securityRisk ?? -1) - (b.securityRisk ?? -1)
                : (b.securityRisk ?? -1) - (a.securityRisk ?? -1),
    );
  const risks = ["critical", "high", "medium", "low"].map((value) => ({
    label: value.toUpperCase(),
    value,
  }));
  return (
    <>
      <FilterBar
        searchPlaceholder="Search hostname, IP, user or OS"
        searchValue={search}
        onSearchChange={setSearch}
        activeFilters={filters}
        onFilterChange={(key, value) =>
          setFilters((f) => ({ ...f, [key]: value }))
        }
        filters={[
          {
            key: "status",
            label: "All endpoint statuses",
            options: ["healthy", "warning", "critical", "offline"].map(
              (value) => ({ label: value, value }),
            ),
          },
          { key: "security", label: "All security risks", options: risks },
          { key: "hardware", label: "All resource impacts", options: risks },
        ]}
      />
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-soc-muted" role="status">
          {filtered.length} of {endpoints.length} endpoints · utilization shown
          as %
        </p>
        <label className="text-xs text-soc-muted">
          Sort by{" "}
          <select
            className="control ml-2"
            aria-label="Sort endpoints"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="security-desc">Security risk: high to low</option>
            <option value="security-asc">Security risk: low to high</option>
            <option value="hardware-desc">Resource impact: high to low</option>
            <option value="hostname">Hostname: A–Z</option>
            <option value="cpu-desc">CPU: high to low</option>
            <option value="seen-desc">Last seen: newest</option>
          </select>
        </label>
      </div>
      <div className="overflow-hidden rounded-lg border border-soc-line bg-soc-panel">
        <DataTable
          data={filtered}
          keyExtractor={(e) => e.id}
          onRowClick={(e) => router.push("/endpoints/" + e.id)}
          columns={[
            {
              key: "hostname",
              header: "Hostname",
              render: (e) => (
                <Link
                  className="link whitespace-nowrap font-medium"
                  href={"/endpoints/" + e.id}
                >
                  {e.hostname}
                </Link>
              ),
            },
            {
              key: "ip",
              header: "IP address",
              render: (e) => (
                <span className="whitespace-nowrap font-mono text-xs">
                  {e.ip}
                </span>
              ),
            },
            { key: "user", header: "Logged-in user", render: (e) => e.user },
            {
              key: "os",
              header: "Operating system",
              render: (e) => (
                <span className="whitespace-nowrap text-xs">{e.os}</span>
              ),
            },
            {
              key: "agent",
              header: "Agent",
              render: (e) => <span className="badge">{e.agentStatus}</span>,
            },
            {
              key: "status",
              header: "Endpoint status",
              render: (e) => <EndpointStatusBadge status={e.status} />,
            },
            {
              key: "security",
              header: "Security risk",
              render: (e) => <SecurityRiskBadge score={e.securityRisk} />,
            },
            {
              key: "hardware",
              header: "Resource impact",
              render: (e) => <HardwareRiskBadge score={e.hardwareRisk} />,
            },
            { key: "cpu", header: "CPU", render: (e) => displayMetric(e.cpu, "%") },
            { key: "gpu", header: "GPU", render: (e) => displayMetric(e.gpu, "%") },
            { key: "ram", header: "RAM", render: (e) => displayMetric(e.ram, "%") },
            {
              key: "seen",
              header: "Last seen",
              render: (e) => (
                <span className="whitespace-nowrap text-xs text-soc-muted">
                  {formatTime(e.lastSeen)}
                </span>
              ),
            },
          ]}
        />
      </div>
    </>
  );
}
