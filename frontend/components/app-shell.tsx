"use client";
import { usePreferences } from "@/lib/preferences";
import { useState } from "react";
import { TimeRangeProvider } from "@/components/time-range";

import { Sidebar } from "@/components/sidebar";
import { TopBar } from "@/components/topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { preferences } = usePreferences();
  const [collapsed, setCollapsed] = useState(false);
  return (
    <TimeRangeProvider>
      <div
        data-density={preferences.density}
        className={`app-shell min-h-screen bg-soc-bg ${collapsed ? "is-collapsed" : ""}`}
      >
        <a href="#main-content" className="skip-link">
          Skip to content
        </a>
        <Sidebar
          collapsed={collapsed}
          onToggle={() => setCollapsed(!collapsed)}
        />
        {/* Main content area - margin matches sidebar width */}
        <div className="app-content min-w-0">
          <TopBar />
          <main id="main-content" tabIndex={-1} className="p-4 xl:p-6">
            {children}
          </main>
        </div>
      </div>
    </TimeRangeProvider>
  );
}
