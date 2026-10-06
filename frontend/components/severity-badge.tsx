import type { Severity } from "@/types";
import { AlertTriangle, AlertCircle, Info, CheckCircle } from "lucide-react";

const config: Record<
  Severity,
  { bg: string; text: string; icon: React.ElementType }
> = {
  critical: {
    bg: "bg-soc-danger-bg",
    text: "text-[#ffd9dc]",
    icon: AlertCircle,
  },
  high: { bg: "bg-soc-warn-bg", text: "text-[#ffe5ba]", icon: AlertTriangle },
  medium: { bg: "bg-soc-accent-bg", text: "text-[#dcecff]", icon: Info },
  low: { bg: "bg-soc-good-bg", text: "text-[#c8f5df]", icon: CheckCircle },
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  const c = config[severity];
  const Icon = c.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold uppercase ${c.bg} ${c.text}`}
    >
      <Icon size={12} />
      {severity}
    </span>
  );
}
