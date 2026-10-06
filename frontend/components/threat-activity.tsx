"use client";
import type { Incident } from "@/types";
import { useTimeRange, inTimeRange } from "@/components/time-range";
export function ThreatActivity({ incidents }: { incidents: Incident[] }) {
  const { range } = useTimeRange();
  const selected = inTimeRange(incidents, range, (i) => i.createdAt);
  const groups = Object.entries(
    selected.reduce<Record<string, number>>((counts, i) => {
      const hour = i.createdAt.slice(11, 13) + ":00";
      return { ...counts, [hour]: (counts[hour] ?? 0) + 1 };
    }, {}),
  ).sort(([a], [b]) => a.localeCompare(b));
  const max = Math.max(...groups.map(([, n]) => n), 1);
  return (
    <div>
      <p className="mb-3 text-xs text-soc-muted">
        {selected.length} incident detections · {range} ending at latest
        observation
      </p>
      <div className="flex h-36 items-end gap-3 border-b border-soc-line">
        {groups.map(([hour, count]) => (
          <div
            key={hour}
            className="flex h-full min-w-0 flex-1 flex-col justify-end text-center"
          >
            <span className="mb-1 text-xs text-soc-muted">{count}</span>
            <div
              role="img"
              aria-label={hour + ": " + count + " incidents"}
              className="mx-auto w-full max-w-16 rounded-t-sm bg-soc-accent/60"
              style={{ height: (count / max) * 90 + "px" }}
            />
            <span className="py-2 text-[10px] text-soc-muted">{hour}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
