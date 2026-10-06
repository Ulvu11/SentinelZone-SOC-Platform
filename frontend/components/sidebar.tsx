"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  Bot,
  ChevronLeft,
  ChevronRight,
  Cpu,
  FileText,
  Gauge,
  Network,
  Radar,
  Search,
  Server,
  Settings,
  Shield,
  ShieldAlert,
  Siren,
} from "lucide-react";

interface NavItem {
  icon: React.ElementType;
  label: string;
  href: string;
}

interface NavGroup {
  title?: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    items: [{ icon: Gauge, label: "Overview", href: "/" }],
  },
  {
    title: "Security",
    items: [
      { icon: Siren, label: "Incidents", href: "/incidents" },
      { icon: ShieldAlert, label: "Alerts", href: "/alerts" },
      { icon: Server, label: "Endpoints", href: "/endpoints" },
      { icon: Cpu, label: "Hardware / CryptoGuard", href: "/hardware" },
    ],
  },
  {
    title: "Monitoring",
    items: [
      { icon: Network, label: "Network", href: "/network" },
      { icon: ShieldAlert, label: "Identity", href: "/identity" },
      { icon: Radar, label: "Honeypots", href: "/honeypots" },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { icon: Search, label: "Threat Hunting", href: "/threat-hunting" },
      { icon: Bot, label: "AI SOC", href: "/ai-soc" },
    ],
  },
  {
    title: "Operations",
    items: [
      { icon: FileText, label: "Reports", href: "/reports" },
      { icon: Settings, label: "Settings", href: "/settings" },
    ],
  },
];

export function Sidebar({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/" || pathname === "/overview";
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <aside
      className={`soc-sidebar fixed top-0 left-0 h-dvh bg-[#0b141f] border-r border-soc-line flex flex-col z-30 ${
        collapsed ? "w-[68px]" : "w-[240px]"
      }`}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-soc-line">
        <div className="w-9 h-9 flex-shrink-0 border border-soc-brand-border rounded-[11px] flex items-center justify-center font-extrabold text-sm bg-soc-brand-bg">
          <Shield size={18} />
        </div>
        {!collapsed && (
          <div className="sidebar-label overflow-hidden">
            <div className="text-[13px] font-bold tracking-[0.05em] text-soc-text">
              SOC PLATFORM
            </div>
            <div className="text-[11px] text-soc-muted">Unified Security</div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav
        aria-label="Main navigation"
        className="flex-1 overflow-y-auto py-3 px-2 space-y-4"
      >
        {navGroups.map((group, gi) => (
          <div key={gi}>
            {group.title && !collapsed && (
              <div className="sidebar-label text-[10px] font-semibold uppercase tracking-[0.12em] text-soc-muted px-3 mb-2">
                {group.title}
              </div>
            )}
            {collapsed && group.title && (
              <div className="h-px bg-soc-line mx-2 mb-2" />
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={item.label}
                    aria-label={item.label}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                      active
                        ? "bg-soc-nav-hover text-soc-text shadow-[inset_3px_0_0_var(--tw-shadow-color)] shadow-soc-accent"
                        : "text-soc-muted hover:text-soc-text hover:bg-soc-nav-hover"
                    } ${collapsed ? "justify-center" : ""}`}
                  >
                    <Icon size={18} className="flex-shrink-0" />
                    {!collapsed && (
                      <span className="sidebar-label">{item.label}</span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-soc-line p-2">
        <button
          onClick={onToggle}
          className="flex items-center justify-center w-full py-2 rounded-lg text-soc-muted hover:text-soc-text hover:bg-soc-nav-hover transition-colors"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>
    </aside>
  );
}
