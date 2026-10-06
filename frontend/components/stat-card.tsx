import type { ReactNode } from "react";

type Tone = "default" | "warn" | "critical" | "good";

const toneStyles: Record<Tone, string> = {
  default: "text-soc-text",
  warn: "text-soc-warn",
  critical: "text-soc-danger",
  good: "text-soc-good",
};

interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
  tone?: Tone;
  icon?: ReactNode;
}

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  icon,
}: StatCardProps) {
  return (
    <div className="bg-gradient-to-b from-soc-panel-alt to-soc-panel border border-soc-line rounded-xl p-4">
      <div className="flex min-h-8 items-start justify-between gap-2 mb-1">
        <span className="text-xs text-soc-muted uppercase tracking-wide">
          {label}
        </span>
        {icon && <span className="shrink-0 text-soc-muted">{icon}</span>}
      </div>
      <div
        className={`${typeof value === "string" && value.length > 18 ? "text-sm leading-relaxed" : "text-2xl"} font-bold mt-1 ${toneStyles[tone]}`}
      >
        {value}
      </div>
      {hint && <div className="text-xs text-soc-muted mt-1">{hint}</div>}
    </div>
  );
}
