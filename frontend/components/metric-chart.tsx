"use client";

import { useId } from "react";
import { formatTime } from "@/lib/format";
import type { TimeSeriesPoint } from "@/types";

interface MetricChartProps {
  data: TimeSeriesPoint[];
  color?: string;
  height?: number;
  label?: string;
}

export function MetricChart({
  data,
  color = "#6ca9ff",
  height = 120,
  label,
}: MetricChartProps) {
  const gradientId = useId();
  if (!data.length) return null;

  const max = Math.max(...data.map((d) => d.value));
  const min = Math.min(...data.map((d) => d.value));
  const range = max - min || 1;

  const points = data
    .map((d, i) => {
      const x = (i / Math.max(data.length - 1, 1)) * 100;
      const y = 100 - ((d.value - min) / range) * 80 - 10;
      return `${x},${y}`;
    })
    .join(" ");

  const areaPoints = `0,100 ${points} 100,100`;

  return (
    <div>
      {label && <div className="text-xs text-soc-muted mb-2">{label}</div>}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        height={height}
        className="w-full"
        role="img"
        aria-label={`${label ?? "Metric"}: ${data.map((d) => d.value).join(", ")}`}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <polygon points={areaPoints} fill={`url(#${gradientId})`} />
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div className="flex justify-between text-[10px] text-soc-muted mt-1">
        <span>{data.length > 0 ? formatTime(data[0].time) : ""}</span>
        <span>Current: {data[data.length - 1]?.value ?? 0}</span>
        <span>
          {data.length > 0 ? formatTime(data[data.length - 1].time) : ""}
        </span>
      </div>
    </div>
  );
}
