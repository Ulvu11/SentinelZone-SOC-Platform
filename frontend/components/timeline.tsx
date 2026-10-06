import { formatTime } from "@/lib/format";
import type { TimelineEvent } from "@/types";
import { AlertCircle, Shield, Bell, Info } from "lucide-react";

const eventIcons: Record<string, React.ElementType> = {
  detection: AlertCircle,
  action: Shield,
  alert: Bell,
  info: Info,
};

const eventColors: Record<string, string> = {
  detection: "text-soc-danger border-soc-danger",
  action: "text-soc-warn border-soc-warn",
  alert: "text-soc-accent border-soc-accent",
  info: "text-soc-muted border-soc-muted",
};

export function Timeline({ events }: { events: TimelineEvent[] }) {
  return (
    <div className="relative">
      <div className="absolute left-[19px] top-0 bottom-0 w-px bg-soc-line" />
      <div className="space-y-4">
        {events.map((event, index) => {
          const category =
            event.category ??
            (event.severity === "critical" || event.severity === "high"
              ? "detection"
              : "alert");
          const Icon = eventIcons[category] ?? Info;
          const color = eventColors[category] ?? eventColors.info;
          return (
            <div key={index} className="relative flex gap-4 pl-0">
              <div
                className={`relative z-10 flex items-center justify-center w-10 h-10 flex-shrink-0 rounded-full border-2 bg-soc-bg ${color}`}
              >
                <Icon size={16} />
              </div>
              <div className="flex-1 pt-1">
                <div className="flex flex-wrap items-center gap-3 mb-0.5">
                  <span className="text-xs font-mono text-soc-muted">
                    {event.time ?? formatTime(event.timestamp)}
                  </span>
                  <span className="text-sm font-semibold text-soc-text">
                    {event.title}
                  </span>
                </div>
                <p className="text-xs text-soc-muted">{event.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
