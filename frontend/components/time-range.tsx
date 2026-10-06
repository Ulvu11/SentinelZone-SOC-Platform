"use client";

import { createContext, useContext, useState } from "react";

export type TimeRange = "1h" | "24h" | "7d";
const RangeContext = createContext<{
  range: TimeRange;
  setRange: (range: TimeRange) => void;
}>({ range: "24h", setRange: () => {} });
export function TimeRangeProvider({ children }: { children: React.ReactNode }) {
  const [range, setRange] = useState<TimeRange>("24h");
  return (
    <RangeContext.Provider value={{ range, setRange }}>
      {children}
    </RangeContext.Provider>
  );
}
export const useTimeRange = () => useContext(RangeContext);

// Live time filters use the current clock, including empty and stale datasets.
export function inTimeRange<T>(
  items: T[],
  range: TimeRange,
  timestamp: (item: T) => string,
): T[] {
  const times = items.map((item) => new Date(timestamp(item)).getTime());
  const latest = Date.now();
  const hours = range === "1h" ? 1 : range === "7d" ? 168 : 24;
  return items.filter((_, index) => times[index] >= latest - hours * 3_600_000 && times[index] <= latest);
}
