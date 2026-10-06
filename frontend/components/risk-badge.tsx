import { ShieldAlert, Cpu } from "lucide-react";

function getRiskColor(score: number | null): string {
  if (score === null) return "text-soc-muted";
  if (score >= 80) return "text-soc-danger";
  if (score >= 50) return "text-soc-warn";
  if (score >= 20) return "text-soc-accent";
  return "text-soc-good";
}

function getRiskLabel(score: number | null): string {
  if (score === null) return "Unavailable";
  if (score >= 80) return "Critical";
  if (score >= 50) return "High";
  if (score >= 20) return "Medium";
  return "Low";
}

export function SecurityRiskBadge({ score }: { score: number | null }) {
  return (
    <div className={`flex items-center gap-1.5 ${getRiskColor(score)}`}>
      <ShieldAlert size={14} />
      <span className="text-sm font-semibold">{score ?? "—"}</span>
      <span className="text-[10px] uppercase font-semibold">
        {getRiskLabel(score).toUpperCase()}
      </span>
    </div>
  );
}

export function HardwareRiskBadge({ score }: { score: number | null }) {
  return (
    <div className={`flex items-center gap-1.5 ${getRiskColor(score)}`}>
      <Cpu size={14} />
      <span className="text-sm font-semibold">{score ?? "—"}</span>
      <span className="text-[10px] uppercase font-semibold">
        {getRiskLabel(score)}
      </span>
    </div>
  );
}

export function RiskScoreBar({
  score,
  label,
}: {
  score: number | null;
  label: string;
}) {
  if (score === null) return <div className="text-xs text-soc-muted">{label}: unavailable</div>;
  const color =
    score >= 80
      ? "bg-soc-danger"
      : score >= 50
        ? "bg-soc-warn"
        : score >= 20
          ? "bg-soc-accent"
          : "bg-soc-good";

  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-xs text-soc-muted">{label}</span>
        <span className={`text-xs font-semibold ${getRiskColor(score)}`}>
          {score}/100 — {getRiskLabel(score)}
        </span>
      </div>
      <div className="w-full h-2 bg-soc-surface rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
