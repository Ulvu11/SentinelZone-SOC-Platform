"use client";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { usePreferences } from "@/lib/preferences";
import Link from "next/link";
import { Bell, Clock, Search, User, Activity } from "lucide-react";
import { SearchDialog } from "@/components/search-dialog";
import { useTimeRange, type TimeRange } from "@/components/time-range";
export function TopBar() {
  const pathname = usePathname();
  const usesSocFeed = ["/", "/overview", "/alerts"].includes(pathname);
  const { preferences } = usePreferences();
  const [searchOpen, setSearchOpen] = useState(false);
  const { range, setRange } = useTimeRange();
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (usesSocFeed) return;
        setSearchOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [usesSocFeed]);
  return (
    <>
      <header className="sticky top-0 z-20 border-b border-soc-line bg-soc-bg/95 backdrop-blur-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 xl:px-6">
          <button
            disabled={usesSocFeed}
            onClick={() => setSearchOpen(true)}
            className="search-trigger flex items-center gap-2 rounded-md border border-soc-line bg-soc-surface px-3 py-2 text-sm text-soc-muted"
            aria-label={usesSocFeed ? "Global search not connected; use the record search below" : "Open global search"}
          >
            <Search size={15} />
            <span className="hidden md:inline">{usesSocFeed ? "Use alert search below" : "Search SOC data"}</span>
            <kbd className="ml-3 text-[10px]">Ctrl+K</kbd>
          </button>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-xs text-soc-muted">
              <Clock size={14} />
              <select
                aria-label="Time range"
                value={range}
                onChange={(e) => setRange(e.target.value as TimeRange)}
                className="control py-2"
              >
                <option value="1h">Last hour</option>
                <option value="24h">Last 24 hours</option>
                <option value="7d">Last 7 days</option>
              </select>
            </label>
            <span className="hidden xl:flex items-center gap-2 text-xs text-soc-muted px-3">
              <Activity size={14} className="text-soc-muted" />
              {"SentinelZone · live backend"}
            </span>
            <Link
              href="/alerts"
              aria-label="View alerts"
              className={
                preferences.highlightAlerts
                  ? "icon-button text-soc-warn"
                  : "icon-button"
              }
            >
              <Bell size={18} />
            </Link>
            <Link
              href="/settings#users"
              aria-label="SOC Analyst profile"
              className="icon-button"
            >
              <User size={18} />
              <span className="hidden 2xl:inline text-xs">SOC Analyst</span>
            </Link>
          </div>
        </div>
      </header>

      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
